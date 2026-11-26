"""Copy the application's SQLite data into an empty MySQL database.

The source SQLite database is read-only. The destination is never dropped or
cleared; this script refuses to run if any destination application table has
rows. It requires the MySQL schema to have been imported first.
"""

from getpass import getpass
from pathlib import Path

from sqlalchemy import create_engine, inspect, select
from sqlalchemy.engine import URL

from models import db  # Import all application models and their metadata.


def main():
    source_path = Path(__file__).with_name("inventory.db")
    if not source_path.is_file():
        raise SystemExit(f"ไม่พบฐานข้อมูลต้นทาง: {source_path}")

    print("ย้ายข้อมูลจาก inventory.db ไปยัง MySQL")
    print("ข้อมูลต้นทางจะไม่ถูกแก้ไข และฐานปลายทางต้องมีตารางครบแต่ยังว่าง")
    host = input("MySQL host [127.0.0.1]: ").strip() or "127.0.0.1"
    port_text = input("MySQL port [3306]: ").strip() or "3306"
    username = input("MySQL user [root]: ").strip() or "root"
    password = getpass("MySQL password (กด Enter หากไม่มีรหัส): ")
    database = input("ชื่อฐานข้อมูล [nonghan_borrow_db]: ").strip() or "nonghan_borrow_db"

    try:
        port = int(port_text)
    except ValueError:
        raise SystemExit("พอร์ตต้องเป็นตัวเลข")

    source_engine = create_engine(URL.create("sqlite", database=str(source_path)))
    target_url = URL.create(
        "mysql+pymysql",
        username=username,
        password=password,
        host=host,
        port=port,
        database=database,
        query={"charset": "utf8mb4"},
    )
    target_engine = create_engine(target_url, pool_pre_ping=True)
    tables = list(db.metadata.sorted_tables)

    try:
        with source_engine.connect() as source, target_engine.connect() as target:
            target_tables = set(inspect(target).get_table_names())
            missing = [table.name for table in tables if table.name not in target_tables]
            if missing:
                raise SystemExit(
                    "ฐานปลายทางยังขาดตาราง: " + ", ".join(missing)
                    + " — กรุณา import nonghan_borrow_db.sql ก่อน"
                )

            populated = []
            for table in tables:
                primary_key_columns = list(table.primary_key.columns)
                if target.execute(select(*primary_key_columns).limit(1)).first() is not None:
                    populated.append(table.name)
            if populated:
                raise SystemExit(
                    "ยกเลิกเพื่อป้องกันข้อมูลซ้ำ: ตารางปลายทางมีข้อมูลแล้ว: "
                    + ", ".join(populated)
                )

            confirm = input(
                f"จะคัดลอกข้อมูลจาก {source_path.name} ไป {database} "
                "พิมพ์ MIGRATE เพื่อยืนยัน: "
            ).strip()
            if confirm != "MIGRATE":
                raise SystemExit("ยกเลิกแล้ว ไม่มีการคัดลอกข้อมูล")

            target.rollback()  # End the read-only inspection transaction.
            counts = {}
            with target.begin():
                for table in tables:
                    rows = [dict(row._mapping) for row in source.execute(select(table))]
                    if rows:
                        target.execute(table.insert(), rows)
                    counts[table.name] = len(rows)

        print("ย้ายข้อมูลสำเร็จ:")
        for table_name, count in counts.items():
            print(f"  {table_name}: {count} แถว")
        print("ตรวจตารางใน phpMyAdmin ได้ ฐานต้นทาง inventory.db ยังอยู่เหมือนเดิม")
    finally:
        source_engine.dispose()
        target_engine.dispose()


if __name__ == "__main__":
    main()
