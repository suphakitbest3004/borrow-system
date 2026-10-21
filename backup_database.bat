@echo off
chcp 65001 >nul
REM ============================================
REM  Backup MySQL Database - ระบบยืม-คืน
REM  ดับเบิลคลิกเพื่อ backup ทุกครั้งก่อนปิดเครื่อง
REM ============================================

set MYSQL_BIN=C:\xampp\mysql\bin
set DB_NAME=nonghan_borrow_db
set BACKUP_DIR=D:\ระบบยืม-คืน\backups
set DATE=%date:~-4%%date:~3,2%%date:~0,2%_%time:~0,2%%time:~3,2%
set DATE=%DATE: =0%

echo.
echo ============================================
echo   Backup MySQL Database
echo   Database: %DB_NAME%
echo ============================================
echo.

if not exist "%BACKUP_DIR%" mkdir "%BACKUP_DIR%"

echo  กำลัง Backup...
"%MYSQL_BIN%\mysqldump.exe" -u root --single-transaction --routines --triggers %DB_NAME% > "%BACKUP_DIR%\%DB_NAME%_%DATE%.sql"

if %errorlevel%==0 (
    echo.
    echo  [OK] Backup สำเร็จ!
    echo  ไฟล์: %BACKUP_DIR%\%DB_NAME%_%DATE%.sql
    echo.
    
    REM ลบไฟล์ backup เก่ากว่า 30 วัน
    forfiles /p "%BACKUP_DIR%" /m "*.sql" /d -30 /c "cmd /c del @path" 2>nul
    echo  (ลบไฟล์ backup เก่ากว่า 30 วันอัตโนมัติ)
) else (
    echo.
    echo  [ERROR] Backup ล้มเหลว!
    echo  ตรวจสอบว่า MySQL กำลังทำงานอยู่หรือไม่
)

echo.
pause
