from datetime import datetime, timedelta
from app import create_app
from models import (
    db, User, Category, Location, FineRate, Supplier, SupplierProduct,
    Equipment, BorrowRequest, Borrowing, ReturnRecord, Fine,
    Maintenance, Notification, PurchaseOrder, PurchaseOrderItem
)

def seed_database():
    app = create_app()
    with app.app_context():
        # Drop all and recreate
        db.drop_all()
        db.create_all()

        print("Creating seed data...")

        # 1. Users
        users_data = [
            User(
                student_or_citizen_id="ADM-001",
                first_name="สมชาย",
                last_name="บริการดี",
                email="admin@nonghan.ac.th",
                phone_number="081-234-5678",
                role="admin",
                line_user_id="Uadmin992817482",
                department="งานพัสดุและสินทรัพย์"
            ),
            User(
                student_or_citizen_id="STF-001",
                first_name="พรทิพย์",
                last_name="ใจประสาน",
                email="staff@nonghan.ac.th",
                phone_number="089-876-5432",
                role="staff",
                line_user_id="Ustaff102938475",
                department="งานพัสดุและสินทรัพย์"
            ),
            User(
                student_or_citizen_id="STD-6630128",
                first_name="ศุภกิจ",
                last_name="ก้าวหน้า",
                email="student@nonghan.ac.th",
                phone_number="095-111-2233",
                role="student",
                line_user_id="Ustudent58291047",
                department="แผนกวิชาช่างอิเล็กทรอนิกส์ (ปวส.2)"
            ),
            User(
                student_or_citizen_id="TCH-002",
                first_name="อาจารย์วรวิทย์",
                last_name="สอนดีเลิศ",
                email="teacher@nonghan.ac.th",
                phone_number="086-444-5566",
                role="teacher",
                line_user_id="Uteacher84920184",
                department="แผนกวิชาคอมพิวเตอร์ธุรกิจ"
            )
        ]
        users_data[0].set_password("admin123")
        users_data[1].set_password("staff123")
        users_data[2].set_password("student123")
        users_data[3].set_password("teacher123")

        db.session.add_all(users_data)
        db.session.commit()

        admin_u = users_data[0]
        staff_u = users_data[1]
        student_u = users_data[2]
        teacher_u = users_data[3]

        # 2. Categories
        cat1 = Category(category_name="ครุภัณฑ์ไฟฟ้าและอิเล็กทรอนิกส์", type="durable_goods")
        cat2 = Category(category_name="ครุภัณฑ์โสตทัศนูปกรณ์", type="durable_goods")
        cat3 = Category(category_name="ครุภัณฑ์วิทยาศาสตร์และการทดลอง", type="durable_goods")
        cat4 = Category(category_name="ครุภัณฑ์ช่างกลและโรงงาน", type="durable_goods")
        cat5 = Category(category_name="วัสดุสิ้นเปลืองงานช่าง", type="material")
        db.session.add_all([cat1, cat2, cat3, cat4, cat5])
        db.session.commit()

        # 3. Locations
        loc1 = Location(location_name="ห้องพัสดุกลาง อาคาร 1 ชั้น 1", description="ตู้จัดเก็บครุภัณฑ์กลาง เบอร์ 01-05")
        loc2 = Location(location_name="ห้องปฏิบัติการอิเล็กทรอนิกส์ อาคาร 3 ชั้น 2", description="ห้อง 321 ชั้นวางเครื่องมือวัด")
        loc3 = Location(location_name="โรงประลองช่างกล อาคารช่าง", description="ล็อกเกอร์เครื่องมือช่าง เบอร์ 12")
        loc4 = Location(location_name="ห้องโสตทัศนศึกษา อาคารวิทยบริการ", description="ตู้เก็บอุปกรณ์มัลติมีเดีย")
        db.session.add_all([loc1, loc2, loc3, loc4])
        db.session.commit()

        # 4. Fine Rates (วันละ 100 บาท ตามหน้า 24, 44)
        fr1 = FineRate(rate_type="คืนเกินกำหนด (ต่อวัน)", amount_per_day=100.0, description="คิดอัตราค่าปรับ 100 บาทต่อวันเมื่อเลยกำหนดเวลาคืน")
        fr2 = FineRate(rate_type="ชำรุดเสียหายเล็กน้อย", amount_per_day=300.0, description="คิดค่าชดเชยการซ่อมแซมเบื้องต้น")
        fr3 = FineRate(rate_type="สูญหายหรือเสียหายสิ้นเชิง", amount_per_day=1500.0, description="คิดราคาชดใช้ตามมูลค่าจัดซื้อของรายการ")
        db.session.add_all([fr1, fr2, fr3])
        db.session.commit()

        # 5. Suppliers
        sup1 = Supplier(
            company_name="บริษัท อุดรวิทยาการศึกษา จำกัด",
            contact_name="คุณกมล คงเกียรติ",
            phone="042-241-890",
            address="142 ถ.โพศรี ต.หมากแข้ง อ.เมือง จ.อุดรธานี",
            email="sales@udonvidhaya.co.th",
            tax_id="0415548001293"
        )
        sup2 = Supplier(
            company_name="บริษัท ไทยอิเล็กทรอนิกส์ อินสตรูเมนท์ จำกัด",
            contact_name="คุณวิภาวรรณ สดใส",
            phone="02-580-9911",
            address="88/9 ถ.วิภาวดีรังสิต แขวงจตุจักร เขตจตุจักร กรุงเทพฯ",
            email="contact@thaielectro-inst.com",
            tax_id="0105552098412"
        )
        sup3 = Supplier(
            company_name="บริษัท สยามไอที แอนด์ ซัพพลาย จำกัด",
            contact_name="คุณธีรพงษ์ วิริยะ",
            phone="02-990-1234",
            address="500/12 ถ.พหลโยธิน แขวงอนุสาวรีย์ เขตบางเขน กรุงเทพฯ",
            email="order@siamitsupply.co.th",
            tax_id="0105560124987"
        )
        db.session.add_all([sup1, sup2, sup3])
        db.session.commit()

        # 6. Equipment with Images
        eq_list = [
            Equipment(
                equipment_code="EQ-EL-001",
                name="ดิจิทัลมัลติมิเตอร์ (Digital Multimeter - Fluke 115)",
                category_id=cat1.category_id,
                location_id=loc2.location_id,
                total_quantity=10,
                available_quantity=8,
                status="available",
                image_path="uploads/multimeter.svg",
                description="เครื่องวัดแรงดันไฟฟ้า กระแสไฟฟ้า และความต้านทาน สำหรับใช้ในห้องทดลองอิเล็กทรอนิกส์"
            ),
            Equipment(
                equipment_code="EQ-AV-002",
                name="เครื่องฉายโปรเจคเตอร์ (Epson EB-X51 3800 ANSI)",
                category_id=cat2.category_id,
                location_id=loc4.location_id,
                total_quantity=5,
                available_quantity=3,
                status="available",
                image_path="uploads/projector.svg",
                description="โปรเจคเตอร์ความสว่างสูง รองรับพอร์ต HDMI และ VGA เหมาะสำหรับห้องเรียนและห้องประชุม"
            ),
            Equipment(
                equipment_code="EQ-SC-003",
                name="เครื่องออสซิลโลสโคปดิจิทัล (Rigol DS1054Z 50MHz 4CH)",
                category_id=cat3.category_id,
                location_id=loc2.location_id,
                total_quantity=6,
                available_quantity=5,
                status="available",
                image_path="uploads/oscilloscope.svg",
                description="เครื่องวิเคราะห์สัญญาณคลื่นไฟฟ้า 4 ช่องสัญญาณ ความถี่ 50MHz พร้อมหน้าจอสี"
            ),
            Equipment(
                equipment_code="EQ-EL-004",
                name="ชุดเครื่องบัดกรีปรับอุณหภูมิ (HAKKO FX-888D)",
                category_id=cat1.category_id,
                location_id=loc2.location_id,
                total_quantity=12,
                available_quantity=10,
                status="available",
                image_path="uploads/soldering.svg",
                description="สถานีหัวแร้งไฟฟ้าควบคุมอุณหภูมิดิจิทัล ปรับความร้อนได้แม่นยำ ปลอดภัยด้วยระบบ ESD safe"
            ),
            Equipment(
                equipment_code="EQ-MT-005",
                name="สว่านกระแทกไร้สาย 12V (Bosch GSB 120-LI)",
                category_id=cat4.category_id,
                location_id=loc3.location_id,
                total_quantity=4,
                available_quantity=4,
                status="available",
                image_path="uploads/drill.svg",
                description="สว่านไร้สายขนาดกะทัดรัดพร้อมแบตเตอรี่ 2 ก้อนและแท่นชาร์จเร็ว"
            ),
            Equipment(
                equipment_code="EQ-AV-006",
                name="กล้องถ่ายภาพดิจิทัล (Canon EOS 200D II Kit 18-55mm)",
                category_id=cat2.category_id,
                location_id=loc4.location_id,
                total_quantity=3,
                available_quantity=2,
                status="available",
                image_path="uploads/camera.svg",
                description="กล้อง DSLR สำหรับบันทึกภาพกิจกรรมและการเรียนการสอน พร้อมเลนส์ซูมและกระเป๋า"
            ),
            Equipment(
                equipment_code="MAT-EL-007",
                name="ลวดบัดกรีผสมฟลักซ์ 0.8mm (Ultracore 500g)",
                category_id=cat5.category_id,
                location_id=loc1.location_id,
                total_quantity=20,
                available_quantity=18,
                status="available",
                image_path="uploads/solder_wire.svg",
                description="ตะกั่วบัดกรีเกรด 60/40 ชนิดม้วน 500 กรัม สำหรับวิชาปฏิบัติงานวงจรอิเล็กทรอนิกส์"
            )
        ]
        db.session.add_all(eq_list)
        db.session.commit()

        # 7. Borrow Requests
        # Request 1: Pending request for testing staff approval (Requirement 2)
        req1 = BorrowRequest(
            user_id=student_u.user_id,
            equipment_id=eq_list[0].equipment_id,
            quantity=1,
            purpose="ใช้ทำโครงงานวิชาไมโครคอนโทรลเลอร์ตรวจวัดค่าเซนเซอร์",
            request_date=datetime.utcnow() - timedelta(hours=2),
            expected_return_date=datetime.utcnow() + timedelta(days=3),
            status="pending"
        )

        # Request 2: Already Approved and active borrowing
        req2 = BorrowRequest(
            user_id=student_u.user_id,
            equipment_id=eq_list[1].equipment_id,
            quantity=1,
            purpose="ใช้พรีเซนต์โครงงานสัมมนาวิชาชีพ แผนกวิชาช่างอิเล็กทรอนิกส์",
            request_date=datetime.utcnow() - timedelta(days=2),
            expected_return_date=datetime.utcnow() + timedelta(days=2),
            status="approved",
            approved_by=staff_u.user_id
        )

        # Request 3: Overdue borrowing for student (to test overdue & fine calculation)
        req3 = BorrowRequest(
            user_id=student_u.user_id,
            equipment_id=eq_list[2].equipment_id,
            quantity=1,
            purpose="ทดสอบสัญญาณวงจรขยายเสียงความถี่สูง",
            request_date=datetime.utcnow() - timedelta(days=7),
            expected_return_date=datetime.utcnow() - timedelta(days=2), # overdue 2 days!
            status="approved",
            approved_by=staff_u.user_id
        )

        # Request 4: Teacher request
        req4 = BorrowRequest(
            user_id=teacher_u.user_id,
            equipment_id=eq_list[5].equipment_id,
            quantity=1,
            purpose="บันทึกภาพการแข่งขันทักษะวิชาชีพ ระดับภาคตะวันออกเฉียงเหนือ",
            request_date=datetime.utcnow() - timedelta(days=5),
            expected_return_date=datetime.utcnow() - timedelta(days=1),
            status="approved",
            approved_by=staff_u.user_id
        )

        db.session.add_all([req1, req2, req3, req4])
        db.session.commit()

        # 8. Borrowing records corresponding to approved requests
        bw2 = Borrowing(
            request_id=req2.request_id,
            user_id=student_u.user_id,
            equipment_id=eq_list[1].equipment_id,
            quantity=1,
            borrow_date=datetime.utcnow() - timedelta(days=2),
            due_date=datetime.utcnow() + timedelta(days=2),
            status="borrowed"
        )

        bw3 = Borrowing(
            request_id=req3.request_id,
            user_id=student_u.user_id,
            equipment_id=eq_list[2].equipment_id,
            quantity=1,
            borrow_date=datetime.utcnow() - timedelta(days=7),
            due_date=datetime.utcnow() - timedelta(days=2), # Overdue by 2 days!
            status="overdue"
        )

        # Teacher already returned
        bw4 = Borrowing(
            request_id=req4.request_id,
            user_id=teacher_u.user_id,
            equipment_id=eq_list[5].equipment_id,
            quantity=1,
            borrow_date=datetime.utcnow() - timedelta(days=5),
            due_date=datetime.utcnow() - timedelta(days=1),
            status="returned"
        )

        db.session.add_all([bw2, bw3, bw4])
        db.session.commit()

        # 9. Return Record for Teacher's completed borrowing
        ret4 = ReturnRecord(
            borrow_id=bw4.borrow_id,
            return_date=datetime.utcnow() - timedelta(days=1),
            condition_status="normal",
            late_days=0,
            received_by=staff_u.user_id
        )
        db.session.add(ret4)
        db.session.commit()

        # 10. Notifications
        notif1 = Notification(
            user_id=student_u.user_id,
            title="✅ อนุมัติคำขอยืมอุปกรณ์เรียบร้อยแล้ว",
            message=f"คำขอยืมรายการ '{eq_list[1].name}' ได้รับการอนุมัติแล้วโดย เจ้าหน้าที่{staff_u.first_name} กรุณาติดต่อรับอุปกรณ์ที่ห้องพัสดุ",
            type="approval",
            channel="system,line,email",
            is_read=False,
            created_at=datetime.utcnow() - timedelta(days=2)
        )
        notif2 = Notification(
            user_id=student_u.user_id,
            title="⚠️ แจ้งเตือน: มีรายการยืมเกินกำหนดคืน",
            message=f"รายการ '{eq_list[2].name}' เกินกำหนดคืนแล้ว 2 วัน มียอดค่าปรับวันละ 100 บาท กรุณานำมาคืนโดยด่วน",
            type="overdue",
            channel="system,line,email",
            is_read=False,
            created_at=datetime.utcnow() - timedelta(hours=5)
        )
        # 11. Supplier Products (สินค้าและพัสดุที่บริษัทคู่ค้าจำหน่าย)
        sp_list = [
            # บริษัท อุดรวิทยาการศึกษา จำกัด
            SupplierProduct(
                supplier_id=sup1.supplier_id,
                equipment_id=eq_list[0].equipment_id,
                product_code="EQ-EL-001",
                product_name="ดิจิทัลมัลติมิเตอร์ (Digital Multimeter - Fluke 115)",
                category_name="ครุภัณฑ์ไฟฟ้าและอิเล็กทรอนิกส์",
                unit="เครื่อง",
                unit_price=4800.0,
                description="เครื่องวัดดิจิทัล True RMS มาตรฐาน Fluke"
            ),
            SupplierProduct(
                supplier_id=sup1.supplier_id,
                equipment_id=None,
                product_code="MT-HK-001",
                product_name="หัวแร้งบัดกรีปรับอุณหภูมิ Hakko FX-888D 70W",
                category_name="วัสดุสิ้นเปลืองช่างอิเล็กทรอนิกส์",
                unit="ชุด",
                unit_price=3450.0,
                description="เครื่องบัดกรีควบคุมความร้อนระบบดิจิทัล"
            ),
            SupplierProduct(
                supplier_id=sup1.supplier_id,
                equipment_id=None,
                product_code="MT-SL-002",
                product_name="ตะกั่วบัดกรี 60/40 พร้อมฟลักซ์ (ม้วน 0.5 กก. 0.8 มม.)",
                category_name="วัสดุสิ้นเปลืองช่างอิเล็กทรอนิกส์",
                unit="ม้วน",
                unit_price=420.0,
                description="ตะกั่วผสมคุณภาพสูงสำหรับงานวงจรพิมพ์"
            ),
            SupplierProduct(
                supplier_id=sup1.supplier_id,
                equipment_id=None,
                product_code="MT-WK-003",
                product_name="ลวดซับตะกั่ว Goot Wick CP-2015 กว้าง 2 มม.",
                category_name="วัสดุสิ้นเปลืองช่างอิเล็กทรอนิกส์",
                unit="ตลับ",
                unit_price=120.0,
                description="ลวดทองแดงถักดูดซับตะกั่วสำหรับถอดอุปกรณ์"
            ),

            # บริษัท ไทยอิเล็กทรอนิกส์ อินสตรูเมนท์ จำกัด
            SupplierProduct(
                supplier_id=sup2.supplier_id,
                equipment_id=eq_list[2].equipment_id,
                product_code="EQ-SC-003",
                product_name="เครื่องออสซิลโลสโคปดิจิทัล (Rigol DS1054Z 50MHz 4CH)",
                category_name="เครื่องมือวัดและทดสอบความเที่ยงตรงสูง",
                unit="เครื่อง",
                unit_price=15900.0,
                description="ออสซิลโลสโคป 4 แชนแนล พร้อมจอสีความละเอียดสูง"
            ),
            SupplierProduct(
                supplier_id=sup2.supplier_id,
                equipment_id=eq_list[3].equipment_id,
                product_code="EQ-EL-004",
                product_name="แหล่งจ่ายไฟกระแสตรงแบบปรับค่าได้ (GW Instek 30V 5A)",
                category_name="ครุภัณฑ์ไฟฟ้าและอิเล็กทรอนิกส์",
                unit="เครื่อง",
                unit_price=7200.0,
                description="Linear DC Power Supply ป้องกันไฟกระชาก"
            ),
            SupplierProduct(
                supplier_id=sup2.supplier_id,
                equipment_id=None,
                product_code="MT-PB-005",
                product_name="สายโพรบออสซิลโลสโคป 100MHz 10:1 (คู่)",
                category_name="เครื่องมือวัดและทดสอบความเที่ยงตรงสูง",
                unit="คู่",
                unit_price=890.0,
                description="สายวัดสัญญาณความถี่สูงแบนด์วิดท์ 100MHz"
            ),
            SupplierProduct(
                supplier_id=sup2.supplier_id,
                equipment_id=None,
                product_code="MT-BB-006",
                product_name="แผงทดลองวงจร Breadboard 830 จุด",
                category_name="วัสดุสิ้นเปลืองช่างอิเล็กทรอนิกส์",
                unit="แผ่น",
                unit_price=160.0,
                description="แผงเสียบอุปกรณ์อิเล็กทรอนิกส์สำหรับการเรียนการสอน"
            ),

            # บริษัท สยามไอที แอนด์ ซัพพลาย จำกัด
            SupplierProduct(
                supplier_id=sup3.supplier_id,
                equipment_id=eq_list[1].equipment_id,
                product_code="EQ-AV-002",
                product_name="เครื่องฉายโปรเจคเตอร์ (Epson EB-X51 3800 ANSI)",
                category_name="โสตทัศนูปกรณ์และการนำเสนอ",
                unit="เครื่อง",
                unit_price=14500.0,
                description="โปรเจคเตอร์สำหรับห้องเรียนพร้อมพอร์ต HDMI"
            ),
            SupplierProduct(
                supplier_id=sup3.supplier_id,
                equipment_id=eq_list[5].equipment_id,
                product_code="EQ-AV-006",
                product_name="กล้องดิจิทัล Mirrorless (Sony Alpha a6400 พร้อมเลนส์ 16-50mm)",
                category_name="โสตทัศนูปกรณ์และการนำเสนอ",
                unit="ชุด",
                unit_price=29900.0,
                description="กล้องบันทึกภาพนิ่งและวิดีโอ 4K สำหรับสื่อการสอน"
            ),
            SupplierProduct(
                supplier_id=sup3.supplier_id,
                equipment_id=None,
                product_code="MT-HD-007",
                product_name="สายสัญญาณ HDMI 2.0 ความยาว 5 เมตร หัวชุบทอง",
                category_name="โสตทัศนูปกรณ์และการนำเสนอ",
                unit="เส้น",
                unit_price=280.0,
                description="สายนำสัญญาณภาพและเสียงความละเอียดสูง"
            ),
            SupplierProduct(
                supplier_id=sup3.supplier_id,
                equipment_id=None,
                product_code="MT-FD-008",
                product_name="แฟลชไดรฟ์ Kingston DataTraveler Exodia 64GB USB 3.2",
                category_name="วัสดุสิ้นเปลืองคอมพิวเตอร์",
                unit="อัน",
                unit_price=180.0,
                description="อุปกรณ์จัดเก็บข้อมูลความเร็วสูง"
            )
        ]
        db.session.add_all(sp_list)
        db.session.commit()

        # 12. Sample Purchase Orders (ประวัติการสั่งซื้อพัสดุและครุภัณฑ์)
        # PO 1: สั่งซื้อจากบริษัท อุดรวิทยาการศึกษา จำกัด (ตรวจรับแล้ว)
        po1 = PurchaseOrder(
            po_number="PO-202610-001",
            supplier_id=sup1.supplier_id,
            order_date=datetime.utcnow() - timedelta(days=15),
            expected_delivery_date=datetime.utcnow() - timedelta(days=8),
            total_amount=28200.0,
            status="received",
            note="จัดซื้อตามงบประมาณพัฒนาห้องปฏิบัติการอิเล็กทรอนิกส์ ภาคเรียนที่ 1",
            created_by=staff_u.user_id
        )
        db.session.add(po1)
        db.session.flush()

        po1_items = [
            PurchaseOrderItem(
                po_id=po1.po_id,
                equipment_id=eq_list[0].equipment_id,
                item_code="EQ-EL-001",
                item_name="ดิจิทัลมัลติมิเตอร์ (Digital Multimeter - Fluke 115)",
                quantity=5,
                unit="เครื่อง",
                unit_price=4800.0,
                total_price=24000.0,
                notes="สำหรับห้องแล็บปฏิบัติการ 2"
            ),
            PurchaseOrderItem(
                po_id=po1.po_id,
                equipment_id=None,
                item_code="MT-SL-002",
                item_name="ตะกั่วบัดกรี 60/40 พร้อมฟลักซ์ (ม้วน 0.5 กก. 0.8 มม.)",
                quantity=10,
                unit="ม้วน",
                unit_price=420.0,
                total_price=4200.0,
                notes="สำรองคลังวัสดุสิ้นเปลือง"
            )
        ]
        db.session.add_all(po1_items)

        # PO 2: สั่งซื้อจากบริษัท ไทยอิเล็กทรอนิกส์ อินสตรูเมนท์ จำกัด (รอรับพัสดุ)
        po2 = PurchaseOrder(
            po_number="PO-202610-002",
            supplier_id=sup2.supplier_id,
            order_date=datetime.utcnow() - timedelta(days=3),
            expected_delivery_date=datetime.utcnow() + timedelta(days=4),
            total_amount=17960.0,
            status="pending",
            note="สั่งซื้อเพื่อทดแทนเครื่องเดิมที่ชำรุดและเตรียมการแข่งขันทักษะ",
            created_by=staff_u.user_id
        )
        db.session.add(po2)
        db.session.flush()

        po2_items = [
            PurchaseOrderItem(
                po_id=po2.po_id,
                equipment_id=eq_list[3].equipment_id,
                item_code="EQ-EL-004",
                item_name="แหล่งจ่ายไฟกระแสตรงแบบปรับค่าได้ (GW Instek 30V 5A)",
                quantity=2,
                unit="เครื่อง",
                unit_price=7200.0,
                total_price=14400.0,
                notes="พร้อมใบรับประกัน 1 ปี"
            ),
            PurchaseOrderItem(
                po_id=po2.po_id,
                equipment_id=None,
                item_code="MT-PB-005",
                item_name="สายโพรบออสซิลโลสโคป 100MHz 10:1 (คู่)",
                quantity=4,
                unit="คู่",
                unit_price=890.0,
                total_price=3560.0,
                notes="สายสำรองเครื่องมือวัด"
            )
        ]
        db.session.add_all(po2_items)

        # PO 3: สั่งซื้อจากบริษัท สยามไอที แอนด์ ซัพพลาย จำกัด (ตรวจรับแล้ว)
        po3 = PurchaseOrder(
            po_number="PO-202610-003",
            supplier_id=sup3.supplier_id,
            order_date=datetime.utcnow() - timedelta(days=10),
            expected_delivery_date=datetime.utcnow() - timedelta(days=5),
            total_amount=30400.0,
            status="received",
            note="จัดซื้อสื่อโสตทัศน์สำหรับห้องประชุมแผนกวิชา",
            created_by=admin_u.user_id
        )
        db.session.add(po3)
        db.session.flush()

        po3_items = [
            PurchaseOrderItem(
                po_id=po3.po_id,
                equipment_id=eq_list[1].equipment_id,
                item_code="EQ-AV-002",
                item_name="เครื่องฉายโปรเจคเตอร์ (Epson EB-X51 3800 ANSI)",
                quantity=2,
                unit="เครื่อง",
                unit_price=14500.0,
                total_price=29000.0,
                notes="ติดตั้งห้องประชุม 1 และ 2"
            ),
            PurchaseOrderItem(
                po_id=po3.po_id,
                equipment_id=None,
                item_code="MT-HD-007",
                item_name="สายสัญญาณ HDMI 2.0 ความยาว 5 เมตร หัวชุบทอง",
                quantity=5,
                unit="เส้น",
                unit_price=280.0,
                total_price=1400.0,
                notes="สายเชื่อมต่อโปรเจคเตอร์"
            )
        ]
        db.session.add_all(po3_items)
        db.session.commit()

        print("Database seeding completed successfully!")

if __name__ == '__main__':
    seed_database()
