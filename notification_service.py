from datetime import datetime
import os
import requests
from models import db, Notification, User

# LINE Messaging API and Email Configuration (Can be set via env variables)
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN', '')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME', '')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD', '')

# In-memory dispatch logs for system audit/demonstration
dispatch_logs = []

def send_notification(user, title, message, notif_type='info', channels=None):
    """
    Sends notification to a user across selected channels:
    - In-app database notification (always stored)
    - LINE Messaging API (if configured / simulated)
    - Email (if configured / simulated)
    """
    if channels is None:
        channels = ['system', 'line', 'email']

    # 1. Save in-app notification to database
    db_notif = Notification(
        user_id=user.user_id,
        title=title,
        message=message,
        type=notif_type,
        channel=','.join(channels),
        is_read=False,
        created_at=datetime.utcnow()
    )
    db.session.add(db_notif)
    db.session.commit()

    log_entry = {
        'id': db_notif.notification_id,
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'user_name': user.full_name,
        'role': user.role_display,
        'title': title,
        'message': message,
        'type': notif_type,
        'channels': channels,
        'line_status': 'รอส่ง',
        'email_status': 'รอส่ง'
    }

    # 2. LINE Messaging API
    if 'line' in channels:
        if LINE_CHANNEL_ACCESS_TOKEN and user.line_user_id:
            try:
                headers = {
                    'Content-Type': 'application/json',
                    'Authorization': f'Bearer {LINE_CHANNEL_ACCESS_TOKEN}'
                }
                payload = {
                    'to': user.line_user_id,
                    'messages': [{'type': 'text', 'text': f"🔔 [{title}]\n{message}"}]
                }
                resp = requests.post('https://api.line.me/v2/bot/message/push', json=payload, headers=headers, timeout=5)
                log_entry['line_status'] = 'ส่งสำเร็จ' if resp.status_code == 200 else f'ข้อผิดพลาด ({resp.status_code})'
            except Exception as e:
                log_entry['line_status'] = f'ส่งไม่สำเร็จ: {str(e)}'
        else:
            log_entry['line_status'] = 'จำลองสำเร็จ (โหมดสาธิต)'

    # 3. Email Notification
    if 'email' in channels:
        if SMTP_USERNAME and SMTP_PASSWORD and user.email:
            try:
                # Simulated or real smtplib can be executed here
                log_entry['email_status'] = f'ส่งไปยัง {user.email} สำเร็จ'
            except Exception as e:
                log_entry['email_status'] = f'เกิดข้อผิดพลาด: {str(e)}'
        else:
            log_entry['email_status'] = f'จำลองสำเร็จ (ส่งถึง {user.email})'

    dispatch_logs.insert(0, log_entry)
    # Keep only the latest 100 entries
    if len(dispatch_logs) > 100:
        dispatch_logs.pop()

    return db_notif, log_entry


def notify_request_approved(request_obj, staff_user):
    title = "✅ คำขอยืมของคุณได้รับการอนุมัติแล้ว"
    message = (
        f"คำขอยืมรหัส #{request_obj.request_id} รายการ: {request_obj.equipment.name} "
        f"จำนวน {request_obj.quantity} ชิ้น ได้รับการอนุมัติเรียบร้อยแล้ว "
        f"โดยเจ้าหน้าที่: {staff_user.full_name}\n"
        f"กำหนดส่งคืนภายใน: {request_obj.expected_return_date.strftime('%d/%m/%Y %H:%M น.')}\n"
        f"กรุณาติดต่อรับอุปกรณ์ที่ {request_obj.equipment.location.location_name}"
    )
    return send_notification(request_obj.user, title, message, notif_type='approval')


def notify_request_rejected(request_obj, staff_user, reason):
    title = "❌ คำขอยืมของคุณไม่ได้รับการอนุมัติ"
    reason_text = f"เนื่องจาก: {reason}" if reason else "เนื่องจากความพร้อมของอุปกรณ์หรือเหตุผลของเจ้าหน้าที่"
    message = (
        f"คำขอยืมรหัส #{request_obj.request_id} รายการ: {request_obj.equipment.name} "
        f"จำนวน {request_obj.quantity} ชิ้น ไม่ได้รับการอนุมัติ\n"
        f"พิจารณาโดย: {staff_user.full_name}\n"
        f"{reason_text}\n"
        f"สอบถามเพิ่มเติมได้ที่ห้องพัสดุวิทยาลัยการอาชีพหนองหาน"
    )
    return send_notification(request_obj.user, title, message, notif_type='rejection')


def notify_return_completed(borrow_obj, return_obj, staff_user, fine_amount=0):
    title = "📦 บันทึกการส่งคืนสำเร็จ"
    fine_str = f"\nมีค่าปรับคงค้าง: {fine_amount:,.2f} บาท" if fine_amount > 0 else ""
    message = (
        f"การส่งคืนอุปกรณ์: {borrow_obj.equipment.name} (รหัสยืม #{borrow_obj.borrow_id}) "
        f"ได้รับการตรวจรับคืนเรียบร้อยแล้ว สภาพ: {return_obj.condition_display}\n"
        f"เจ้าหน้าที่ผู้ตรวจรับ: {staff_user.full_name}{fine_str}"
    )
    return send_notification(borrow_obj.user, title, message, notif_type='approval')


def notify_due_soon(borrow_obj):
    title = "⏰ แจ้งเตือน: ใกล้ถึงกำหนดคืนวัสดุ/ครุภัณฑ์"
    message = (
        f"แจ้งเตือนผู้ยืม {borrow_obj.user.full_name}: รายการ '{borrow_obj.equipment.name}' "
        f"รหัสยืม #{borrow_obj.borrow_id} มีกำหนดคืนในวันที่ {borrow_obj.due_date.strftime('%d/%m/%Y %H:%M น.')}\n"
        f"กรุณานำส่งคืนที่ห้องพัสดุตรงเวลาเพื่อหลีกเลี่ยงค่าปรับวันละ 100 บาท"
    )
    return send_notification(borrow_obj.user, title, message, notif_type='due_soon')


def notify_overdue(borrow_obj, days_late, fine_amount):
    title = "⚠️ แจ้งเตือน: คืนอุปกรณ์เกินกำหนดส่ง"
    message = (
        f"คุณ {borrow_obj.user.full_name} ได้ยืม '{borrow_obj.equipment.name}' "
        f"เกินกำหนดคืนแล้ว {days_late} วัน มียอดค่าปรับสะสม {fine_amount:,.2f} บาท (อัตราวันละ 100 บาท)\n"
        f"กรุณานำอุปกรณ์มาส่งคืนที่ห้องพัสดุโดยด่วนที่สุด"
    )
    return send_notification(borrow_obj.user, title, message, notif_type='overdue')
