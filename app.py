import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from functools import wraps
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    session, jsonify, g, abort, Response
)
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from sqlalchemy.engine import URL

from models import (
    db, User, Category, Location, FineRate, Supplier, SupplierProduct,
    Equipment, BorrowRequest, Borrowing, ReturnRecord, Fine,
    Maintenance, Notification, PurchaseOrder, PurchaseOrderItem,
    GoodsReceipt, GoodsReceiptItem, IssueReport, SystemSetting
)
import notification_service

# Local .env values are used for development; host-provided environment
# variables take precedence.
load_dotenv(Path(__file__).with_name('.env'))

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), 'static', 'uploads')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp', 'svg'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'nonghan-borrow-return-system-secret-key-2026'
    
    # -------------------------------------------------------------
    # DATABASE CONFIGURATION (รองรับทั้ง MySQL และ SQLite)
    # -------------------------------------------------------------
    DB_TYPE = os.environ.get('DB_TYPE', 'mysql').lower()  # กำหนด 'mysql' หรือ 'sqlite'
    MYSQL_HOST = os.environ.get('MYSQL_HOST', '127.0.0.1')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'nonghan_borrow_db')

    db_path = os.path.join(os.path.dirname(__file__), 'inventory.db')
    if os.environ.get('VERCEL') and not os.environ.get('DATABASE_URL') and DB_TYPE == 'sqlite':
        import shutil
        tmp_db = '/tmp/inventory.db'
        if not os.path.exists(tmp_db) and os.path.exists(db_path):
            try:
                shutil.copy2(db_path, tmp_db)
            except Exception:
                pass
        db_path = tmp_db
    if os.environ.get('DATABASE_URL'):
        app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL')
    elif DB_TYPE == 'mysql':
        import socket
        mysql_online = False
        conn_timeout = 3.0 if MYSQL_HOST not in ('127.0.0.1', 'localhost') else 0.5
        try:
            with socket.create_connection((MYSQL_HOST, MYSQL_PORT), timeout=conn_timeout):
                mysql_online = True
        except OSError:
            mysql_online = False

        if mysql_online:
            app.config['SQLALCHEMY_DATABASE_URI'] = URL.create(
                'mysql+pymysql', username=MYSQL_USER, password=MYSQL_PASSWORD,
                host=MYSQL_HOST, port=MYSQL_PORT, database=MYSQL_DB,
                query={'charset': 'utf8mb4'}
            )
        else:
            raise RuntimeError(f"Cannot connect to MySQL at {MYSQL_HOST}:{MYSQL_PORT}; refusing to use SQLite")
    elif DB_TYPE == 'sqlite':
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    else:
        raise ValueError("DB_TYPE must be 'mysql' or 'sqlite'")

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

    db.init_app(app)

    with app.app_context():
        db.create_all()

    # Context processor for templates
    @app.context_processor
    def inject_global_data():
        current_user = None
        unread_count = 0
        if 'user_id' in session:
            current_user = User.query.get(session['user_id'])
            if current_user:
                unread_count = Notification.query.filter_by(
                    user_id=current_user.user_id, is_read=False
                ).count()
        
        # Pending requests & issues count for staff/admin badge
        pending_requests_count = 0
        pending_issues_count = 0
        if current_user and current_user.role in ['admin', 'staff']:
            pending_requests_count = BorrowRequest.query.filter_by(status='pending').count()
            pending_issues_count = IssueReport.query.filter_by(status='pending').count()

        return {
            'current_user': current_user,
            'unread_count': unread_count,
            'pending_requests_count': pending_requests_count,
            'pending_issues_count': pending_issues_count,
            'now': datetime.utcnow()
        }

    # Auth decorators
    def login_required(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                flash('กรุณาเข้าสู่ระบบก่อนทำรายการ', 'warning')
                return redirect(url_for('login', next=request.url))
            return f(*args, **kwargs)
        return decorated_function

    def roles_required(*allowed_roles):
        def decorator(f):
            @wraps(f)
            def decorated_function(*args, **kwargs):
                if 'user_id' not in session:
                    flash('กรุณาเข้าสู่ระบบก่อนทำรายการ', 'warning')
                    return redirect(url_for('login', next=request.url))
                user = User.query.get(session['user_id'])
                if not user or user.role not in allowed_roles:
                    flash('คุณไม่มีสิทธิ์เข้าถึงหน้านี้ (ต้องการสิทธิ์: ' + ', '.join(allowed_roles) + ')', 'danger')
                    return redirect(url_for('index'))
                return f(*args, **kwargs)
            return decorated_function
        return decorator

    # -------------------------------------------------------------
    # AUTHENTICATION
    # -------------------------------------------------------------
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            # Support quick demo login
            quick_role = request.form.get('quick_role')
            if quick_role:
                demo_user = User.query.filter_by(role=quick_role).first()
                if demo_user:
                    session['user_id'] = demo_user.user_id
                    flash(f'เข้าสู่ระบบในฐานะ {demo_user.role_display}: {demo_user.full_name} เรียบร้อยแล้ว', 'success')
                    return redirect(url_for('profile' if demo_user.role in ['student', 'teacher'] else 'admin_requests'))

            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')

            user = User.query.filter_by(email=email).first()
            if user and user.check_password(password):
                session['user_id'] = user.user_id
                flash(f'ยินดีต้อนรับคุณ {user.full_name}', 'success')
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                if user.role in ['admin', 'staff']:
                    return redirect(url_for('admin_requests'))
                return redirect(url_for('catalog'))
            else:
                flash('อีเมลหรือรหัสผ่านไม่ถูกต้อง กรุณาลองใหม่อีกครั้ง', 'danger')

        return render_template('auth/login.html')

    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if request.method == 'POST':
            student_or_citizen_id = request.form.get('student_or_citizen_id', '').strip()
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            phone_number = request.form.get('phone_number', '').strip()
            role = request.form.get('role', 'student')
            line_user_id = request.form.get('line_user_id', '').strip()
            department = request.form.get('department', '').strip()

            if not all([student_or_citizen_id, first_name, last_name, email, password]):
                flash('กรุณากรอกข้อมูลที่จำเป็นให้ครบถ้วน', 'danger')
                return render_template('auth/register.html')

            if User.query.filter_by(email=email).first():
                flash('อีเมลนี้ถูกใช้งานในระบบแล้ว กรุณาใช้อีเมลอื่น', 'danger')
                return render_template('auth/register.html')

            new_user = User(
                student_or_citizen_id=student_or_citizen_id,
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone_number=phone_number,
                role=role if role in ['student', 'teacher'] else 'student',
                line_user_id=line_user_id,
                department=department
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()

            # Welcome notification
            notification_service.send_notification(
                new_user,
                "🎉 ยินดีต้อนรับสู่ระบบยืม-คืน",
                f"สวัสดีคุณ {new_user.full_name} บัญชีของคุณได้รับการลงทะเบียนเรียบร้อยแล้ว สามารถเริ่มยื่นคำขอยืมวัสดุ/ครุภัณฑ์ได้ทันที",
                notif_type='info'
            )

            flash('ลงทะเบียนสำเร็จ! กรุณาเข้าสู่ระบบด้วยบัญชีของคุณ', 'success')
            return redirect(url_for('login'))

        return render_template('auth/register.html')

    @app.route('/logout')
    def logout():
        session.clear()
        flash('ออกจากระบบเรียบร้อยแล้ว', 'info')
        return redirect(url_for('login'))

    # -------------------------------------------------------------
    # SEO & SEARCH ENGINE INDEXING (Google, Bing, etc.)
    # -------------------------------------------------------------
    @app.route('/robots.txt')
    def robots_txt():
        return app.send_static_file('robots.txt')

    @app.route('/sitemap.xml')
    def sitemap_xml():
        host_url = request.host_url.rstrip('/')
        xml_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
    <url>
        <loc>{host_url}/</loc>
        <changefreq>daily</changefreq>
        <priority>1.0</priority>
    </url>
    <url>
        <loc>{host_url}/catalog</loc>
        <changefreq>daily</changefreq>
        <priority>0.9</priority>
    </url>
    <url>
        <loc>{host_url}/login</loc>
        <changefreq>monthly</changefreq>
        <priority>0.5</priority>
    </url>
</urlset>"""
        return Response(xml_content, mimetype='application/xml')

    # -------------------------------------------------------------
    # HOME / LANDING PAGE
    # -------------------------------------------------------------
    @app.route('/')
    def index():
        if 'user_id' in session:
            user = User.query.get(session['user_id'])
            if user:
                if user.role in ['admin', 'staff']:
                    return redirect(url_for('admin_requests'))
                return redirect(url_for('catalog'))
        return render_template('index.html')

    # -------------------------------------------------------------
    # CATALOG & BROWSING
    # -------------------------------------------------------------
    @app.route('/catalog')
    def catalog():
        search_query = request.args.get('q', '').strip()
        cat_id = request.args.get('category', type=int)
        item_type = request.args.get('type', '').strip()

        query = Equipment.query
        if search_query:
            query = query.filter(
                (Equipment.name.ilike(f'%{search_query}%')) |
                (Equipment.equipment_code.ilike(f'%{search_query}%')) |
                (Equipment.description.ilike(f'%{search_query}%'))
            )
        if cat_id:
            query = query.filter_by(category_id=cat_id)
        if item_type:
            query = query.join(Category).filter(Category.type == item_type)

        items = query.order_by(Equipment.name.asc()).all()
        categories = Category.query.order_by(Category.category_name.asc()).all()

        return render_template('catalog.html', items=items, categories=categories, search_query=search_query, selected_cat=cat_id, item_type=item_type)

    # -------------------------------------------------------------
    # REQUIREMENT 1: USER PROFILE (ดูข้อมูลส่วนตัวของตนเอง)
    # -------------------------------------------------------------
    @app.route('/profile')
    @login_required
    def profile():
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))

        # User's borrow requests
        requests_list = BorrowRequest.query.filter_by(user_id=user.user_id).order_by(BorrowRequest.request_date.desc()).all()
        
        # User's active borrowings
        active_borrowings = Borrowing.query.filter_by(user_id=user.user_id).filter(
            Borrowing.status.in_(['borrowed', 'overdue'])
        ).order_by(Borrowing.due_date.asc()).all()

        # User's returned history
        history_borrowings = Borrowing.query.filter_by(user_id=user.user_id, status='returned').order_by(Borrowing.borrow_date.desc()).all()

        # Stats
        stats = {
            'total_requests': len(requests_list),
            'active_borrowed': len(active_borrowings),
            'completed_returns': len(history_borrowings),
            'overdue_count': sum(1 for b in active_borrowings if b.is_overdue)
        }

        fine_rate = FineRate.query.filter_by(rate_type='คืนเกินกำหนด (ต่อวัน)').first()
        fine_per_day = fine_rate.amount_per_day if fine_rate else 100.0

        return render_template(
            'profile.html',
            user=user,
            requests_list=requests_list,
            active_borrowings=active_borrowings,
            history_borrowings=history_borrowings,
            stats=stats,
            fine_per_day=fine_per_day
        )

    @app.route('/profile/update', methods=['POST'])
    @login_required
    def profile_update():
        flash('ข้อมูลส่วนตัวของผู้ใช้งานสามารถดูได้อย่างเดียว ไม่อนุญาตให้แก้ไขด้วยตนเองตามนโยบายระบบ', 'warning')
        return redirect(url_for('profile'))

    # -------------------------------------------------------------
    # BORROW REQUEST SUBMISSION (USER)
    # -------------------------------------------------------------
    @app.route('/borrow/request', methods=['POST'])
    @login_required
    def submit_borrow_request():
        equipment_id = request.form.get('equipment_id', type=int)
        quantity = request.form.get('quantity', 1, type=int)
        expected_days = request.form.get('expected_days', 3, type=int)
        expected_date_str = request.form.get('expected_return_date')
        purpose = request.form.get('purpose', '').strip()

        equipment = Equipment.query.get_or_404(equipment_id)

        # Validation: check available stock
        if equipment.available_quantity < quantity or quantity < 1:
            flash(f'จำนวนคงเหลือของ {equipment.name} ไม่เพียงพอสำหรับการยืม (คงเหลือ {equipment.available_quantity})', 'danger')
            return redirect(url_for('catalog'))

        # Calculate return date
        if expected_date_str:
            try:
                expected_return_date = datetime.strptime(expected_date_str, '%Y-%m-%d')
                expected_return_date = expected_return_date.replace(hour=16, minute=30)
            except ValueError:
                expected_return_date = datetime.utcnow() + timedelta(days=max(1, expected_days))
        else:
            expected_return_date = datetime.utcnow() + timedelta(days=max(1, expected_days))

        borrow_req = BorrowRequest(
            user_id=session['user_id'],
            equipment_id=equipment.equipment_id,
            quantity=quantity,
            purpose=purpose,
            request_date=datetime.utcnow(),
            expected_return_date=expected_return_date,
            status='pending'
        )
        db.session.add(borrow_req)
        db.session.commit()

        # Send alert to staff users
        staff_users = User.query.filter(User.role.in_(['staff', 'admin'])).all()
        current_u = User.query.get(session['user_id'])
        for staff in staff_users:
            notification_service.send_notification(
                staff,
                f"📥 มีคำขอยืมใหม่ #{borrow_req.request_id}",
                f"ผู้ยืม: {current_u.full_name} ({current_u.role_display})\n"
                f"รายการ: {equipment.name} จำนวน {quantity} รายการ\n"
                f"วัตถุประสงค์: {purpose or 'ไม่ได้ระบุ'}\n"
                f"กรุณาตรวจสอบและกดอนุมัติที่หน้าจัดการคำขอยืม",
                notif_type='info'
            )

        flash('ยื่นคำขอยืมสำเร็จ! ระบบได้ส่งข้อมูลให้เจ้าหน้าที่ตรวจสอบและรอการอนุมัติแล้ว', 'success')
        return redirect(url_for('profile'))

    # -------------------------------------------------------------
    # REQUIREMENT 2: STAFF APPROVAL & NOTIFICATIONS (เจ้าหน้าที่กดอนุมัติ)
    # -------------------------------------------------------------
    @app.route('/admin/requests')
    @roles_required('admin', 'staff')
    def admin_requests():
        status_filter = request.args.get('status', 'pending')
        query = BorrowRequest.query
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        
        requests_list = query.order_by(BorrowRequest.request_date.desc()).all()
        return render_template('admin/requests.html', requests_list=requests_list, current_filter=status_filter)

    @app.route('/admin/requests/<int:request_id>/approve', methods=['POST'])
    @roles_required('admin', 'staff')
    def approve_request(request_id):
        borrow_req = BorrowRequest.query.get_or_404(request_id)
        if borrow_req.status != 'pending':
            flash('คำขอยืมนี้ได้รับการดำเนินการไปแล้ว', 'warning')
            return redirect(url_for('admin_requests'))

        equipment = borrow_req.equipment
        if equipment.available_quantity < borrow_req.quantity:
            flash(f'ไม่สามารถอนุมัติได้ เนื่องจากอุปกรณ์คงเหลือไม่พอ (มีเพียง {equipment.available_quantity})', 'danger')
            return redirect(url_for('admin_requests'))

        staff_user = User.query.get(session['user_id'])

        # 1. Update stock
        equipment.available_quantity -= borrow_req.quantity
        if equipment.available_quantity == 0:
            equipment.status = 'borrowed'

        # 2. Update request status
        borrow_req.status = 'approved'
        borrow_req.approved_by = staff_user.user_id

        # 3. Create active Borrowing record
        borrowing = Borrowing(
            request_id=borrow_req.request_id,
            user_id=borrow_req.user_id,
            equipment_id=borrow_req.equipment_id,
            quantity=borrow_req.quantity,
            borrow_date=datetime.utcnow(),
            due_date=borrow_req.expected_return_date,
            status='borrowed'
        )
        db.session.add(borrowing)
        db.session.commit()

        # 4. Trigger Automatic Notification (LINE, Email, In-app)
        notification_service.notify_request_approved(borrow_req, staff_user)

        flash(f'อนุมัติคำขอยืม #{borrow_req.request_id} ({borrow_req.user.full_name}) สำเร็จ และส่งข้อความแจ้งเตือนเรียบร้อยแล้ว!', 'success')
        return redirect(url_for('admin_requests'))

    @app.route('/admin/requests/<int:request_id>/reject', methods=['POST'])
    @roles_required('admin', 'staff')
    def reject_request(request_id):
        borrow_req = BorrowRequest.query.get_or_404(request_id)
        if borrow_req.status != 'pending':
            flash('คำขอยืมนี้ได้รับการดำเนินการไปแล้ว', 'warning')
            return redirect(url_for('admin_requests'))

        reason = request.form.get('rejection_reason', '').strip()
        staff_user = User.query.get(session['user_id'])

        borrow_req.status = 'rejected'
        borrow_req.rejection_reason = reason
        borrow_req.approved_by = staff_user.user_id
        db.session.commit()

        # Trigger Rejection Notification
        notification_service.notify_request_rejected(borrow_req, staff_user, reason)

        flash(f'ปฏิเสธคำขอยืม #{borrow_req.request_id} แล้ว พร้อมส่งข้อความแจ้งเตือนสาเหตุไปยังผู้ยืม', 'info')
        return redirect(url_for('admin_requests'))

    # -------------------------------------------------------------
    # AUTO-NUMBER GENERATORS (ระบบสร้างรหัสอัตโนมัติ)
    # -------------------------------------------------------------
    def generate_next_equipment_codes(count=1):
        """
        สร้างรหัสพัสดุ/ครุภัณฑ์ถัดไปอัตโนมัติ (Auto-number) ในรูปแบบ EQ-0001, EQ-0002...
        ตรวจจับตัวเลขสูงสุดจากรหัสที่มีอยู่เดิมในระบบเพื่อรับประกันว่าไม่ซ้ำและเรียงลำดับต่อเนื่อง
        """
        all_codes = [eq.equipment_code for eq in Equipment.query.all() if eq.equipment_code]
        max_num = 0
        pattern = re.compile(r'(\d+)$')
        for c in all_codes:
            m = pattern.search(c.strip())
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        generated = []
        curr = max_num + 1
        existing_set = set(all_codes)
        while len(generated) < count:
            candidate = f"EQ-{curr:04d}"
            if candidate not in existing_set:
                generated.append(candidate)
                existing_set.add(candidate)
            curr += 1
        return generated

    def generate_next_equipment_code():
        """สร้างรหัสพัสดุ/ครุภัณฑ์เดี่ยวถัดไป"""
        return generate_next_equipment_codes(1)[0]

    def generate_next_product_code():
        """
        สร้างรหัสสินค้าบริษัทคู่ค้าถัดไปอัตโนมัติ (Auto-number) ในรูปแบบ PRD-0001, PRD-0002...
        """
        all_codes = [p.product_code for p in SupplierProduct.query.all() if p.product_code]
        max_num = 0
        pattern = re.compile(r'(\d+)$')
        for c in all_codes:
            m = pattern.search(c.strip())
            if m:
                try:
                    num = int(m.group(1))
                    if num > max_num:
                        max_num = num
                except ValueError:
                    pass

        curr = max_num + 1
        existing_set = set(all_codes)
        while True:
            candidate = f"PRD-{curr:04d}"
            if candidate not in existing_set:
                return candidate
            curr += 1

    def generate_next_po_number():
        """
        สร้างเลขที่ใบสั่งซื้ออัตโนมัติ ในรูปแบบ PO-YYYYMM-XXXX
        """
        now_str = datetime.utcnow().strftime('%Y%m')
        prefix = f"PO-{now_str}-"
        matching = PurchaseOrder.query.filter(PurchaseOrder.po_number.like(f'{prefix}%')).all()
        max_num = 0
        for po in matching:
            suffix = po.po_number[len(prefix):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
        curr = max(len(matching) + 1, max_num + 1)
        while True:
            candidate = f"{prefix}{curr:04d}"
            if not PurchaseOrder.query.filter_by(po_number=candidate).first():
                return candidate
            curr += 1

    def generate_next_receipt_number(receipt_type='purchase'):
        """
        สร้างเลขที่ใบรับเข้าอัตโนมัติ ในรูปแบบ GR-YYYYMM-XXXX, DR-YYYYMM-XXXX ฯลฯ
        """
        now_str = datetime.utcnow().strftime('%Y%m')
        prefix = {'purchase': 'GR', 'direct': 'DR', 'donation': 'DN', 'transfer': 'TF'}.get(receipt_type, 'GR')
        pattern = f"{prefix}-{now_str}-"
        matching = GoodsReceipt.query.filter(GoodsReceipt.receipt_number.like(f'{pattern}%')).all()
        max_num = 0
        for gr in matching:
            suffix = gr.receipt_number[len(pattern):]
            if suffix.isdigit():
                max_num = max(max_num, int(suffix))
        curr = max(len(matching) + 1, max_num + 1)
        while True:
            candidate = f"{pattern}{curr:04d}"
            if not GoodsReceipt.query.filter_by(receipt_number=candidate).first():
                return candidate
            curr += 1

    @app.route('/api/equipment/next-code')
    @roles_required('admin', 'staff')
    def api_equipment_next_code():
        """API ส่งคืนรหัสครุภัณฑ์ถัดไปสำหรับ UI Pre-fill"""
        count = request.args.get('count', 1, type=int)
        if count > 1:
            codes = generate_next_equipment_codes(count)
            return jsonify({'success': True, 'next_codes': codes, 'next_code': codes[0]})
        code = generate_next_equipment_code()
        return jsonify({'success': True, 'next_code': code})

    @app.route('/api/products/next-code')
    @roles_required('admin', 'staff')
    def api_products_next_code():
        """API ส่งคืนรหัสสินค้าคู่ค้าถัดไปสำหรับ UI Pre-fill"""
        code = generate_next_product_code()
        return jsonify({'success': True, 'next_code': code})

    # -------------------------------------------------------------
    # REQUIREMENT 3 & 4: CRUD EQUIPMENT & IMAGE UPLOAD
    # -------------------------------------------------------------
    @app.route('/admin/equipment')
    @roles_required('admin', 'staff')
    def admin_equipment():
        search_query = request.args.get('q', '').strip()
        cat_id = request.args.get('category', type=int)

        query = Equipment.query
        if search_query:
            query = query.filter(
                (Equipment.name.ilike(f'%{search_query}%')) |
                (Equipment.equipment_code.ilike(f'%{search_query}%'))
            )
        if cat_id:
            query = query.filter_by(category_id=cat_id)

        equipment_list = query.order_by(Equipment.equipment_id.desc()).all()
        categories = Category.query.all()
        locations = Location.query.all()
        next_equipment_code = generate_next_equipment_code()
        return render_template(
            'admin/equipment.html',
            equipment_list=equipment_list,
            categories=categories,
            locations=locations,
            search_query=search_query,
            selected_cat=cat_id,
            next_equipment_code=next_equipment_code
        )

    @app.route('/admin/equipment/add', methods=['POST'])
    @roles_required('admin', 'staff')
    def add_equipment():
        code = request.form.get('equipment_code', '').strip()
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        location_id = request.form.get('location_id', type=int)
        total_quantity = request.form.get('total_quantity', 1, type=int)
        status = request.form.get('status', 'available')
        description = request.form.get('description', '').strip()

        if not name or not category_id or not location_id:
            flash('กรุณากรอกชื่อ หมวดหมู่ และสถานที่จัดเก็บให้ครบถ้วน', 'danger')
            return redirect(url_for('admin_equipment'))

        # Auto-number fallback if empty
        if not code:
            code = generate_next_equipment_code()
        elif Equipment.query.filter_by(equipment_code=code).first():
            flash(f'รหัสพัสดุ/ครุภัณฑ์ {code} มีอยู่ในระบบแล้ว', 'danger')
            return redirect(url_for('admin_equipment'))

        # Handle Image Upload (Requirement 4)
        image_path = None
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

        eq = Equipment(
            equipment_code=code,
            name=name,
            category_id=category_id,
            location_id=location_id,
            total_quantity=total_quantity,
            available_quantity=total_quantity,
            status=status,
            image_path=image_path,
            description=description
        )
        db.session.add(eq)
        db.session.commit()

        flash(f'เพิ่มรายการ {name} (รหัส {code}) สำเร็จเรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_equipment'))

    @app.route('/admin/equipment/new')
    @roles_required('admin', 'staff')
    def new_equipment_page():
        categories = Category.query.order_by(Category.category_name.asc()).all()
        locations = Location.query.order_by(Location.location_name.asc()).all()
        next_equipment_code = generate_next_equipment_code()
        return render_template(
            'admin/equipment_new.html',
            categories=categories,
            locations=locations,
            next_equipment_code=next_equipment_code
        )

    @app.route('/admin/equipment/batch-add', methods=['POST'])
    @roles_required('admin', 'staff')
    def batch_add_equipment():
        codes = request.form.getlist('equipment_code[]')
        names = request.form.getlist('name[]')
        category_ids = request.form.getlist('category_id[]')
        location_ids = request.form.getlist('location_id[]')
        total_quantities = request.form.getlist('total_quantity[]')
        statuses = request.form.getlist('status[]')
        descriptions = request.form.getlist('description[]')

        images = request.files.getlist('image[]')

        added_count = 0
        duplicate_codes = []

        existing_codes_in_batch = set(eq.equipment_code for eq in Equipment.query.all() if eq.equipment_code)
        pattern = re.compile(r'(\d+)$')

        def get_batch_next_code():
            max_num = 0
            for c in existing_codes_in_batch:
                m = pattern.search(c.strip())
                if m:
                    try:
                        n = int(m.group(1))
                        if n > max_num:
                            max_num = n
                    except ValueError:
                        pass
            curr = max_num + 1
            while True:
                candidate = f"EQ-{curr:04d}"
                if candidate not in existing_codes_in_batch:
                    existing_codes_in_batch.add(candidate)
                    return candidate
                curr += 1

        for i in range(len(names)):
            name = names[i].strip() if i < len(names) else ''
            if not name:
                continue

            code = codes[i].strip() if i < len(codes) else ''
            if not code:
                code = get_batch_next_code()
            elif code in existing_codes_in_batch:
                duplicate_codes.append(code)
                continue
            else:
                existing_codes_in_batch.add(code)

            try:
                cat_id = int(category_ids[i]) if i < len(category_ids) and category_ids[i] else 1
            except (ValueError, TypeError):
                cat_id = 1

            try:
                loc_id = int(location_ids[i]) if i < len(location_ids) and location_ids[i] else 1
            except (ValueError, TypeError):
                loc_id = 1

            try:
                qty = int(total_quantities[i]) if i < len(total_quantities) and total_quantities[i] else 1
            except (ValueError, TypeError):
                qty = 1

            status = statuses[i] if i < len(statuses) and statuses[i] else 'available'
            desc = descriptions[i].strip() if i < len(descriptions) else ''

            image_path = None
            if i < len(images) and images[i] and images[i].filename != '' and allowed_file(images[i].filename):
                file = images[i]
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{i}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                image_path = f"uploads/{filename}"

            eq = Equipment(
                equipment_code=code,
                name=name,
                category_id=cat_id,
                location_id=loc_id,
                total_quantity=qty,
                available_quantity=qty,
                status=status,
                image_path=image_path,
                description=desc
            )
            db.session.add(eq)
            added_count += 1

        if added_count > 0:
            db.session.commit()
            if duplicate_codes:
                flash(f'บันทึกข้อมูลทั้งหมดสำเร็จ {added_count} รายการ (ข้ามรหัสที่ซ้ำในระบบ: {", ".join(duplicate_codes)})', 'warning')
            else:
                flash(f'บันทึกข้อมูลวัสดุและครุภัณฑ์ทั้งหมด ({added_count} รายการ) สำเร็จเรียบร้อยแล้ว!', 'success')
        else:
            if duplicate_codes:
                flash(f'ไม่สามารถบันทึกได้ เนื่องจากรหัสพัสดุซ้ำในระบบ: {", ".join(duplicate_codes)}', 'danger')
            else:
                flash('ไม่พบข้อมูลที่จะบันทึก กรุณากรอกชื่อรายการอย่างน้อย 1 รายการ', 'warning')

        return redirect(url_for('admin_equipment'))

    @app.route('/admin/equipment/<int:equipment_id>/edit', methods=['POST'])
    @roles_required('admin', 'staff')
    def edit_equipment(equipment_id):
        eq = Equipment.query.get_or_404(equipment_id)
        eq.name = request.form.get('name', eq.name).strip()
        eq.category_id = request.form.get('category_id', eq.category_id, type=int)
        eq.location_id = request.form.get('location_id', eq.location_id, type=int)
        
        diff_total = request.form.get('total_quantity', eq.total_quantity, type=int) - eq.total_quantity
        eq.total_quantity += diff_total
        eq.available_quantity = max(0, eq.available_quantity + diff_total)

        eq.status = request.form.get('status', eq.status)
        eq.description = request.form.get('description', eq.description).strip()

        # Handle Image Upload (Requirement 4)
        if 'image' in request.files:
            file = request.files['image']
            if file and file.filename != '' and allowed_file(file.filename):
                filename = secure_filename(f"{int(datetime.utcnow().timestamp())}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                eq.image_path = f"uploads/{filename}"

        db.session.commit()
        flash(f'แก้ไขข้อมูล {eq.name} สำเร็จเรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_equipment'))

    @app.route('/admin/equipment/<int:equipment_id>/delete', methods=['POST'])
    @roles_required('admin')
    def delete_equipment(equipment_id):
        eq = Equipment.query.get_or_404(equipment_id)
        # Check if active borrowings exist
        active_b = Borrowing.query.filter_by(equipment_id=eq.equipment_id, status='borrowed').first()
        if active_b:
            flash('ไม่สามารถลบได้ เนื่องจากมีรายการที่กำลังถูกยืมอยู่ในขณะนี้', 'danger')
            return redirect(url_for('admin_equipment'))

        name = eq.name
        db.session.delete(eq)
        db.session.commit()
        flash(f'ลบรายการ {name} ออกจากระบบเรียบร้อยแล้ว', 'info')
        return redirect(url_for('admin_equipment'))

    # -------------------------------------------------------------
    # REQUIREMENT 3: CRUD USERS (จัดการผู้ใช้งาน)
    # -------------------------------------------------------------
    @app.route('/admin/users')
    @roles_required('admin')
    def admin_users():
        search_query = request.args.get('q', '').strip()
        role_filter = request.args.get('role', '').strip()

        query = User.query
        if search_query:
            query = query.filter(
                (User.first_name.ilike(f'%{search_query}%')) |
                (User.last_name.ilike(f'%{search_query}%')) |
                (User.email.ilike(f'%{search_query}%')) |
                (User.student_or_citizen_id.ilike(f'%{search_query}%'))
            )
        if role_filter:
            query = query.filter_by(role=role_filter)

        users_list = query.order_by(User.user_id.desc()).all()
        return render_template('admin/users.html', users_list=users_list, search_query=search_query, selected_role=role_filter)

    @app.route('/admin/users/add', methods=['POST'])
    @roles_required('admin')
    def add_user():
        student_or_citizen_id = request.form.get('student_or_citizen_id', '').strip()
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '123456')
        phone_number = request.form.get('phone_number', '').strip()
        role = request.form.get('role', 'student')
        department = request.form.get('department', '').strip()
        line_user_id = request.form.get('line_user_id', '').strip()

        if not student_or_citizen_id or not first_name or not last_name or not email:
            flash('กรุณากรอกรหัสประจำตัว ชื่อ-สกุล และอีเมลให้ครบถ้วน', 'danger')
            return redirect(url_for('admin_users'))

        if User.query.filter_by(email=email).first():
            flash('อีเมลนี้มีอยู่ในระบบแล้ว', 'danger')
            return redirect(url_for('admin_users'))

        u = User(
            student_or_citizen_id=student_or_citizen_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            phone_number=phone_number,
            role=role,
            department=department,
            line_user_id=line_user_id
        )
        u.set_password(password)
        db.session.add(u)
        db.session.commit()

        flash(f'เพิ่มผู้ใช้งาน {u.full_name} ({u.role_display}) สำเร็จเรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/edit', methods=['POST'])
    @roles_required('admin')
    def edit_user(user_id):
        u = User.query.get_or_404(user_id)
        u.first_name = request.form.get('first_name', u.first_name).strip()
        u.last_name = request.form.get('last_name', u.last_name).strip()
        u.student_or_citizen_id = request.form.get('student_or_citizen_id', u.student_or_citizen_id).strip()
        u.phone_number = request.form.get('phone_number', u.phone_number).strip()
        u.role = request.form.get('role', u.role)
        u.department = request.form.get('department', u.department).strip()
        u.line_user_id = request.form.get('line_user_id', u.line_user_id).strip()

        new_password = request.form.get('new_password', '').strip()
        if new_password:
            u.set_password(new_password)

        db.session.commit()
        flash(f'แก้ไขข้อมูลผู้ใช้ {u.full_name} เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_users'))

    @app.route('/admin/users/<int:user_id>/delete', methods=['POST'])
    @roles_required('admin')
    def delete_user(user_id):
        if user_id == session.get('user_id'):
            flash('ไม่สามารถลบบัญชีของตนเองที่กำลังเข้าสู่ระบบอยู่ได้', 'danger')
            return redirect(url_for('admin_users'))

        u = User.query.get_or_404(user_id)
        name = u.full_name

        # 1. ตรวจสอบว่ามีรายการอุปกรณ์ที่กำลังยืมอยู่และยังไม่คืนหรือไม่
        active_bw_count = Borrowing.query.filter_by(user_id=u.user_id).filter(
            Borrowing.status.in_(['borrowed', 'overdue'])
        ).count()
        if active_bw_count > 0:
            flash(f'ไม่สามารถลบ {name} ได้ เนื่องจากยังมีรายการอุปกรณ์ที่กำลังยืมอยู่ {active_bw_count} รายการ กรุณาบันทึกการรับคืนอุปกรณ์เข้าคลังก่อนทำการลบ', 'danger')
            return redirect(url_for('admin_users'))

        force = request.form.get('force') == '1'

        # 2. ตรวจสอบประวัติธุรกรรมที่ผูกอยู่
        requests_count = BorrowRequest.query.filter_by(user_id=u.user_id).count()
        approved_count = BorrowRequest.query.filter_by(approved_by=u.user_id).count()
        borrowings_count = Borrowing.query.filter_by(user_id=u.user_id).count()
        returns_count = ReturnRecord.query.filter_by(received_by=u.user_id).count()
        fines_count = Fine.query.filter_by(issued_by=u.user_id).count()
        pos_count = PurchaseOrder.query.filter_by(created_by=u.user_id).count()
        goods_count = GoodsReceipt.query.filter_by(received_by=u.user_id).count()
        maint_count = Maintenance.query.filter_by(recorded_by=u.user_id).count()

        total_linked = (requests_count + approved_count + borrowings_count + 
                        returns_count + fines_count + pos_count + goods_count + maint_count)

        if total_linked > 0 and not force:
            reasons = []
            if borrowings_count > 0: reasons.append(f"ประวัติการยืม-คืน {borrowings_count} รายการ")
            if requests_count > 0: reasons.append(f"คำขอยืม {requests_count} รายการ")
            if approved_count > 0: reasons.append(f"เป็นผู้อนุมัติคำขอ {approved_count} รายการ")
            if pos_count > 0: reasons.append(f"เป็นผู้สร้างใบสั่งซื้อ {pos_count} รายการ")
            if returns_count > 0: reasons.append(f"เป็นผู้ตรวจรับคืน {returns_count} รายการ")
            if fines_count > 0: reasons.append(f"เป็นผู้ออกใบเสร็จค่าปรับ {fines_count} รายการ")

            flash(
                f'ไม่สามารถลบ {name} ได้ เนื่องจากมีประวัติธุรกรรมในระบบผูกอยู่ ({", ".join(reasons)}) '
                f'ตามมาตรฐานความปลอดภัยฐานข้อมูล (Foreign Key Constraint) หากต้องการลบจริงๆ ให้เลือกตัวเลือก "ลบประวัติที่เกี่ยวข้องทั้งหมด"',
                'warning'
            )
            return redirect(url_for('admin_users'))

        try:
            # ลบการแจ้งเตือนของผู้ใช้
            Notification.query.filter_by(user_id=u.user_id).delete()

            if force:
                # กรณีที่ผู้ใช้เป็นเจ้าหน้าที่ที่เคยอนุมัติ/รับของ ให้โอนย้ายไปยังแอดมินคนอื่น เพื่อไม่ให้เอกสารเสีย
                another_admin = User.query.filter(User.role == 'admin', User.user_id != u.user_id).first()
                fallback_admin_id = another_admin.user_id if another_admin else None

                BorrowRequest.query.filter_by(approved_by=u.user_id).update({'approved_by': fallback_admin_id})
                ReturnRecord.query.filter_by(received_by=u.user_id).update({'received_by': fallback_admin_id})
                Fine.query.filter_by(issued_by=u.user_id).update({'issued_by': fallback_admin_id})
                PurchaseOrder.query.filter_by(created_by=u.user_id).update({'created_by': fallback_admin_id})
                GoodsReceipt.query.filter_by(received_by=u.user_id).update({'received_by': fallback_admin_id})
                Maintenance.query.filter_by(recorded_by=u.user_id).update({'recorded_by': fallback_admin_id})

                # ลบประวัติการยืมและคำขอของผู้ใช้นี้
                for bw in Borrowing.query.filter_by(user_id=u.user_id).all():
                    if bw.return_record:
                        if bw.return_record.fine:
                            db.session.delete(bw.return_record.fine)
                        db.session.delete(bw.return_record)
                    db.session.delete(bw)

                for br in BorrowRequest.query.filter_by(user_id=u.user_id).all():
                    db.session.delete(br)

            db.session.delete(u)
            db.session.commit()
            flash(f'ลบผู้ใช้งาน {name} ออกจากระบบเรียบร้อยแล้ว', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาดในการลบผู้ใช้งาน {name}: มีข้อมูลประวัติการยืมหรือเอกสารในระบบผูกอยู่ (MySQL Foreign Key Constraint)', 'danger')

        return redirect(url_for('admin_users'))

    # -------------------------------------------------------------
    # REQUIREMENT 3: CRUD CATEGORIES (เพิ่มประเภทใหม่ได้)
    # -------------------------------------------------------------
    @app.route('/admin/categories')
    @roles_required('admin', 'staff')
    def admin_categories():
        categories = Category.query.all()
        return render_template('admin/categories.html', categories=categories)

    @app.route('/admin/categories/add', methods=['POST'])
    @roles_required('admin', 'staff')
    def add_category():
        category_name = request.form.get('category_name', '').strip()
        cat_type = request.form.get('type', 'durable_goods')
        if not category_name:
            flash('กรุณาระบุชื่อหมวดหมู่/ประเภท', 'danger')
            return redirect(url_for('admin_categories'))

        cat = Category(category_name=category_name, type=cat_type)
        db.session.add(cat)
        db.session.commit()
        flash(f'เพิ่มประเภทใหม่ "{category_name}" สำเร็จเรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_categories'))

    @app.route('/admin/categories/<int:category_id>/edit', methods=['POST'])
    @roles_required('admin', 'staff')
    def edit_category(category_id):
        cat = Category.query.get_or_404(category_id)
        cat.category_name = request.form.get('category_name', cat.category_name).strip()
        cat.type = request.form.get('type', cat.type)
        db.session.commit()
        flash(f'แก้ไขประเภท "{cat.category_name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_categories'))

    @app.route('/admin/categories/<int:category_id>/delete', methods=['POST'])
    @roles_required('admin')
    def delete_category(category_id):
        cat = Category.query.get_or_404(category_id)
        if cat.equipment_list:
            flash(f'ไม่สามารถลบประเภท "{cat.category_name}" ได้ เนื่องจากมีรายการวัสดุ/ครุภัณฑ์ผูกอยู่', 'danger')
            return redirect(url_for('admin_categories'))
        name = cat.category_name
        db.session.delete(cat)
        db.session.commit()
        flash(f'ลบประเภท "{name}" สำเร็จแล้ว', 'info')
        return redirect(url_for('admin_categories'))

    # -------------------------------------------------------------
    # CRUD LOCATIONS & MASTER DATA
    # -------------------------------------------------------------
    @app.route('/admin/locations')
    @roles_required('admin', 'staff')
    def admin_locations():
        locations = Location.query.all()
        return render_template('admin/locations.html', locations=locations)

    @app.route('/admin/locations/add', methods=['POST'])
    @roles_required('admin', 'staff')
    def add_location():
        name = request.form.get('location_name', '').strip()
        desc = request.form.get('description', '').strip()
        if not name:
            flash('กรุณาระบุชื่อสถานที่จัดเก็บ', 'danger')
            return redirect(url_for('admin_locations'))
        loc = Location(location_name=name, description=desc)
        db.session.add(loc)
        db.session.commit()
        flash(f'เพิ่มสถานที่จัดเก็บ "{name}" สำเร็จ', 'success')
        return redirect(url_for('admin_locations'))

    @app.route('/admin/locations/<int:location_id>/edit', methods=['POST'])
    @roles_required('admin', 'staff')
    def edit_location(location_id):
        loc = Location.query.get_or_404(location_id)
        loc.location_name = request.form.get('location_name', loc.location_name).strip()
        loc.description = request.form.get('description', loc.description).strip()
        db.session.commit()
        flash(f'แก้ไขสถานที่จัดเก็บ "{loc.location_name}" เรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_locations'))

    @app.route('/admin/locations/<int:location_id>/delete', methods=['POST'])
    @roles_required('admin')
    def delete_location(location_id):
        loc = Location.query.get_or_404(location_id)
        if loc.equipment_list:
            flash(f'ไม่สามารถลบสถานที่ "{loc.location_name}" ได้เนื่องจากมีอุปกรณ์จัดเก็บอยู่', 'danger')
            return redirect(url_for('admin_locations'))
        name = loc.location_name
        db.session.delete(loc)
        db.session.commit()
        flash(f'ลบสถานที่ "{name}" สำเร็จแล้ว', 'info')
        return redirect(url_for('admin_locations'))

    # -------------------------------------------------------------
    # RETURNS & FINES (การรับคืนอุปกรณ์และการคำนวณค่าปรับ)
    # -------------------------------------------------------------
    @app.route('/admin/returns', methods=['GET', 'POST'])
    @roles_required('admin', 'staff')
    def admin_returns():
        if request.method == 'POST':
            borrow_id = request.form.get('borrow_id', type=int)
            condition_status = request.form.get('condition_status', 'normal')
            damage_fine = request.form.get('damage_fine', 0.0, type=float)
            payment_method = request.form.get('payment_method', 'cash')
            payment_status = request.form.get('payment_status', 'unpaid')

            borrowing = Borrowing.query.get_or_404(borrow_id)
            staff_user = User.query.get(session['user_id'])
            return_time = datetime.utcnow()

            # Calculate late days & late fine (100 THB/day)
            late_days = 0
            late_fine = 0.0
            if return_time > borrowing.due_date:
                diff = return_time - borrowing.due_date
                late_days = max(1, diff.days + (1 if diff.seconds > 3600 else 0))
                # Check fine rate from DB
                fr = FineRate.query.filter_by(rate_type='คืนเกินกำหนด (ต่อวัน)').first()
                rate_per_day = fr.amount_per_day if fr else 100.0
                late_fine = late_days * rate_per_day

            total_fine = late_fine + damage_fine

            # Create Return Record
            return_record = ReturnRecord(
                borrow_id=borrowing.borrow_id,
                return_date=return_time,
                condition_status=condition_status,
                late_days=late_days,
                received_by=staff_user.user_id
            )
            db.session.add(return_record)

            # Update Borrowing status
            borrowing.status = 'returned'

            # Update Equipment stock
            equipment = borrowing.equipment
            equipment.available_quantity += borrowing.quantity
            if condition_status == 'damaged':
                equipment.status = 'damaged'
            elif equipment.available_quantity > 0 and equipment.status == 'borrowed':
                equipment.status = 'available'

            db.session.commit()

            # Create Fine record if there's a fine
            fine_record = None
            if total_fine > 0:
                receipt_no = f"REC-{datetime.now().strftime('%Y%m%d')}-{return_record.return_id:04d}"
                fine_record = Fine(
                    return_id=return_record.return_id,
                    receipt_number=receipt_no,
                    late_fine=late_fine,
                    damage_fine=damage_fine,
                    total_fine=total_fine,
                    payment_method=payment_method,
                    payment_status=payment_status,
                    paid_at=return_time if payment_status == 'paid' else None,
                    issued_by=staff_user.user_id
                )
                db.session.add(fine_record)
                db.session.commit()

            # Notify borrower
            notification_service.notify_return_completed(borrowing, return_record, staff_user, total_fine)

            flash(f'บันทึกการรับคืนรายการ {equipment.name} เรียบร้อยแล้ว (ผู้ยืม: {borrowing.user.full_name})', 'success')
            if fine_record:
                return redirect(url_for('fine_receipt', fine_id=fine_record.fine_id))
            return redirect(url_for('admin_returns'))

        # GET method
        search_q = request.args.get('q', '').strip()
        query = Borrowing.query.filter(Borrowing.status.in_(['borrowed', 'overdue']))
        if search_q:
            query = query.join(User).join(Equipment).filter(
                (User.first_name.ilike(f'%{search_q}%')) |
                (User.last_name.ilike(f'%{search_q}%')) |
                (User.student_or_citizen_id.ilike(f'%{search_q}%')) |
                (Equipment.name.ilike(f'%{search_q}%')) |
                (Equipment.equipment_code.ilike(f'%{search_q}%'))
            )

        active_borrowings = query.order_by(Borrowing.borrow_date.desc()).all()
        recent_returns = ReturnRecord.query.order_by(ReturnRecord.return_date.desc()).limit(15).all()

        return render_template(
            'admin/returns.html',
            active_borrowings=active_borrowings,
            recent_returns=recent_returns,
            search_q=search_q
        )

    # -------------------------------------------------------------
    # RECEIPT & FINES VIEW
    # -------------------------------------------------------------
    @app.route('/admin/fines')
    @roles_required('admin', 'staff')
    def admin_fines():
        fines_list = Fine.query.order_by(Fine.fine_id.desc()).all()
        fine_rate = FineRate.query.filter_by(rate_type='คืนเกินกำหนด (ต่อวัน)').first()
        return render_template('admin/fines.html', fines_list=fines_list, fine_rate=fine_rate)

    @app.route('/admin/fines/<int:fine_id>/pay', methods=['POST'])
    @roles_required('admin', 'staff')
    def pay_fine(fine_id):
        fine = Fine.query.get_or_404(fine_id)
        payment_method = request.form.get('payment_method', 'cash')
        fine.payment_status = 'paid'
        fine.payment_method = payment_method
        fine.paid_at = datetime.utcnow()
        db.session.commit()
        flash(f'บันทึกการชำระเงินใบเสร็จเลขที่ {fine.receipt_number} สำเร็จแล้ว', 'success')
        return redirect(url_for('fine_receipt', fine_id=fine.fine_id))

    @app.route('/admin/fines/receipt/<int:fine_id>')
    @login_required
    def fine_receipt(fine_id):
        fine = Fine.query.get_or_404(fine_id)
        # Security check: User can only view their own receipt, Staff/Admin can view all
        current_u = User.query.get(session['user_id'])
        if current_u.role in ['student', 'teacher'] and fine.return_record.borrowing.user_id != current_u.user_id:
            abort(403)
        return render_template('admin/receipt.html', fine=fine)

    # -------------------------------------------------------------
    # PRINT DOCUMENTS (เอกสารพิมพ์)
    # -------------------------------------------------------------
    @app.route('/admin/borrowings/<int:borrow_id>/permit')
    @roles_required('admin', 'staff')
    def borrow_permit(borrow_id):
        """ใบอนุญาตยืมวัสดุ/ครุภัณฑ์ สำหรับพิมพ์"""
        borrowing = Borrowing.query.get_or_404(borrow_id)
        return render_template('admin/borrow_permit.html', borrowing=borrowing)

    @app.route('/admin/returns/<int:return_id>/form')
    @roles_required('admin', 'staff')
    def return_form_print(return_id):
        """ใบรับคืนวัสดุ/ครุภัณฑ์ สำหรับพิมพ์"""
        ret = ReturnRecord.query.get_or_404(return_id)
        return render_template('admin/return_form.html', ret=ret)

    @app.route('/admin/reports/monthly')
    @roles_required('admin', 'staff')
    def report_monthly():
        """รายงานสรุปการยืม-คืนรายเดือน"""
        from calendar import monthrange
        now_date = datetime.utcnow()
        selected_month = request.args.get('month', now_date.month, type=int)
        year_be = request.args.get('year', now_date.year + 543, type=int)
        year_ce = year_be - 543
        if not 1 <= selected_month <= 12:
            selected_month = now_date.month
        if year_ce < 1900 or year_ce > 2100:
            year_ce = now_date.year
            year_be = year_ce + 543
        _, last_day = monthrange(year_ce, selected_month)
        start_date = datetime(year_ce, selected_month, 1)
        end_date = datetime(year_ce, selected_month, last_day, 23, 59, 59)
        month_names_th = ['มกราคม','กุมภาพันธ์','มีนาคม','เมษายน','พฤษภาคม','มิถุนายน',
                          'กรกฎาคม','สิงหาคม','กันยายน','ตุลาคม','พฤศจิกายน','ธันวาคม']
        month_name = month_names_th[selected_month - 1]
        borrowings = Borrowing.query.filter(
            Borrowing.borrow_date >= start_date,
            Borrowing.borrow_date <= end_date
        ).order_by(Borrowing.borrow_date.asc()).all()
        fines = Fine.query.join(ReturnRecord).filter(
            ReturnRecord.return_date >= start_date,
            ReturnRecord.return_date <= end_date
        ).all()
        requests_month = BorrowRequest.query.filter(
            BorrowRequest.request_date >= start_date,
            BorrowRequest.request_date <= end_date
        ).all()
        total_requests = len(requests_month)
        approved_count = sum(1 for r in requests_month if r.status == 'approved')
        returned_count = sum(1 for b in borrowings if b.status == 'returned')
        overdue_count = sum(1 for b in borrowings if b.is_overdue)
        total_fines = sum(f.total_fine for f in fines)
        pending_fines = sum(f.total_fine for f in fines if f.payment_status == 'unpaid')
        return render_template(
            'admin/report_monthly.html',
            borrowings=borrowings, fines=fines, month_name=month_name, year=year_be,
            selected_month=selected_month, total_requests=total_requests,
            approved_count=approved_count, returned_count=returned_count,
            overdue_count=overdue_count, total_fines=total_fines, pending_fines=pending_fines
        )

    @app.route('/admin/reports/equipment-register')
    @roles_required('admin', 'staff')
    def report_equipment_register():
        """ทะเบียนครุภัณฑ์ สำหรับพิมพ์"""
        selected_type = request.args.get('type', '').strip()
        selected_status = request.args.get('status', '').strip()
        query = Equipment.query
        if selected_type:
            query = query.join(Category).filter(Category.type == selected_type)
        if selected_status:
            query = query.filter(Equipment.status == selected_status)
        equipment_list = query.order_by(Equipment.equipment_code.asc()).all()
        available_count = sum(1 for e in equipment_list if e.status == 'available')
        borrowed_count = sum(1 for e in equipment_list if e.status == 'borrowed')
        damaged_count = sum(1 for e in equipment_list if e.status in ['damaged', 'maintenance'])
        total_qty = sum(e.total_quantity for e in equipment_list)
        available_qty = sum(e.available_quantity for e in equipment_list)
        return render_template(
            'admin/report_equipment_register.html',
            equipment_list=equipment_list, selected_type=selected_type, selected_status=selected_status,
            available_count=available_count, borrowed_count=borrowed_count,
            damaged_count=damaged_count, total_qty=total_qty, available_qty=available_qty
        )

    @app.route('/admin/reports/borrow-return')
    @roles_required('admin', 'staff')
    def report_borrow_return():
        """
        รายงานการยืมและการคืนวัสดุ/ครุภัณฑ์
        สามารถระบุสาขาวิชา/แผนกวิชา และระบุช่วงวัน/เดือน/ปี ได้ ทั้งรายงานการยืมและรายงานการคืน
        """
        report_type = request.args.get('type', 'borrow').strip()  # 'borrow', 'return', 'all'
        selected_dept = request.args.get('department', '').strip()
        start_date_str = request.args.get('start_date', '').strip()
        end_date_str = request.args.get('end_date', '').strip()

        now = datetime.utcnow()
        if not start_date_str:
            start_date_str = now.replace(day=1).strftime('%Y-%m-%d')
        if not end_date_str:
            end_date_str = now.strftime('%Y-%m-%d')

        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        except ValueError:
            start_date = now.replace(day=1)
            start_date_str = start_date.strftime('%Y-%m-%d')

        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        except ValueError:
            end_date = now.replace(hour=23, minute=59, second=59)
            end_date_str = now.strftime('%Y-%m-%d')

        # Collect available departments from DB + default college departments
        default_depts = [
            "แผนกวิชาช่างอิเล็กทรอนิกส์",
            "แผนกวิชาช่างยนต์",
            "แผนกวิชาช่างไฟฟ้ากำลัง",
            "แผนกวิชาช่างกลโรงงาน",
            "แผนกวิชาคอมพิวเตอร์ธุรกิจ",
            "แผนกวิชาการบัญชี",
            "แผนกวิชาการตลาด",
            "งานพัสดุและสินทรัพย์"
        ]
        db_depts = [d[0] for d in db.session.query(User.department).filter(User.department.isnot(None), User.department != '').distinct().all() if d[0]]
        all_departments = sorted(list(set(default_depts + db_depts)))

        borrow_items = []
        return_items = []

        # Query Borrowings
        if report_type in ['borrow', 'all']:
            b_query = Borrowing.query.join(User).join(Equipment).filter(
                Borrowing.borrow_date >= start_date,
                Borrowing.borrow_date <= end_date
            )
            if selected_dept:
                b_query = b_query.filter(User.department.ilike(f'%{selected_dept}%'))
            borrow_items = b_query.order_by(Borrowing.borrow_date.desc()).all()

        # Query Returns
        if report_type in ['return', 'all']:
            r_query = ReturnRecord.query.join(Borrowing, ReturnRecord.borrow_id == Borrowing.borrow_id)\
                                        .join(User, Borrowing.user_id == User.user_id)\
                                        .join(Equipment, Borrowing.equipment_id == Equipment.equipment_id)\
                                        .filter(
                                            ReturnRecord.return_date >= start_date,
                                            ReturnRecord.return_date <= end_date
                                        )
            if selected_dept:
                r_query = r_query.filter(User.department.ilike(f'%{selected_dept}%'))
            return_items = r_query.order_by(ReturnRecord.return_date.desc()).all()

        # Summary statistics
        total_borrow_count = len(borrow_items)
        total_borrow_qty = sum(b.quantity for b in borrow_items)
        active_borrow_count = sum(1 for b in borrow_items if b.status in ['borrowed', 'overdue'])
        overdue_borrow_count = sum(1 for b in borrow_items if b.is_overdue)

        total_return_count = len(return_items)
        total_return_qty = sum(r.borrowing.quantity for r in return_items if r.borrowing)
        normal_return_count = sum(1 for r in return_items if r.condition_status == 'normal')
        damaged_return_count = sum(1 for r in return_items if r.condition_status in ['damaged', 'lost'])
        total_fines = sum(r.fine.total_fine for r in return_items if r.fine)

        # Thai formatted dates for display
        thai_months = ['ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.']
        s_parts = start_date_str.split('-')
        e_parts = end_date_str.split('-')
        start_date_th = f"{int(s_parts[2])} {thai_months[int(s_parts[1])-1]} {int(s_parts[0]) + 543}"
        end_date_th = f"{int(e_parts[2])} {thai_months[int(e_parts[1])-1]} {int(e_parts[0]) + 543}"

        return render_template(
            'admin/report_borrow_return.html',
            report_type=report_type,
            selected_dept=selected_dept,
            start_date=start_date_str,
            end_date=end_date_str,
            start_date_th=start_date_th,
            end_date_th=end_date_th,
            all_departments=all_departments,
            borrow_items=borrow_items,
            return_items=return_items,
            total_borrow_count=total_borrow_count,
            total_borrow_qty=total_borrow_qty,
            active_borrow_count=active_borrow_count,
            overdue_borrow_count=overdue_borrow_count,
            total_return_count=total_return_count,
            total_return_qty=total_return_qty,
            normal_return_count=normal_return_count,
            damaged_return_count=damaged_return_count,
            total_fines=total_fines,
            today_date=f"{now.day} {thai_months[now.month-1]} {now.year + 543}"
        )

    # -------------------------------------------------------------
    # NOTIFICATIONS & DISPATCH LOG
    # -------------------------------------------------------------

    @app.route('/notifications')
    @login_required
    def notifications_page():
        user = User.query.get(session['user_id'])
        notifs = Notification.query.filter_by(user_id=user.user_id).order_by(Notification.created_at.desc()).all()
        # Mark all as read
        for n in notifs:
            n.is_read = True
        db.session.commit()
        return render_template('notifications.html', notifications=notifs)

    @app.route('/api/notifications/unread_count')
    def api_unread_count():
        if 'user_id' not in session:
            return jsonify({'count': 0})
        count = Notification.query.filter_by(user_id=session['user_id'], is_read=False).count()
        return jsonify({'count': count})

    @app.route('/admin/notification-logs')
    @roles_required('admin', 'staff')
    def notification_logs():
        logs = notification_service.dispatch_logs
        return render_template('admin/notification_logs.html', logs=logs)

    def get_issue_contact_info():
        """ดึงข้อมูลติดต่อด่วนสำหรับแสดงในหน้ารายงานปัญหา (สามารถแก้ไขได้โดยเจ้าหน้าที่/Admin)"""
        return {
            'title': SystemSetting.get('contact_title', 'ติดต่อด่วนงานพัสดุ'),
            'location': SystemSetting.get('contact_location', 'อาคาร 1 ชั้น 1 งานพัสดุ วิทยาลัยการอาชีพหนองหาน'),
            'hours': SystemSetting.get('contact_hours', 'วันจันทร์ - ศุกร์ (08:30 - 16:30 น.)'),
            'phone': SystemSetting.get('contact_phone', '042-xxxxxx หรือ โทรศัพท์ภายใน 104, 105'),
            'line': SystemSetting.get('contact_line', '@nonghan_parcel (ID Line: nonghan104)'),
            'note': SystemSetting.get('contact_note', 'กรณีอุปกรณ์ชำรุดฉุกเฉินในการเรียนการสอน หรือพบเหตุขัดข้องเร่งด่วน สามารถติดต่อห้องพัสดุได้ทันที')
        }

    # -------------------------------------------------------------
    # USER ISSUE REPORTING & TICKETS (ระบบรายงานปัญหาการใช้งาน)
    # -------------------------------------------------------------
    @app.route('/issues', methods=['GET', 'POST'])
    @login_required
    def user_issues():
        """หน้าสำหรับผู้ใช้งานยื่นรายงานปัญหา และดูประวัติปัญหาที่ตนเองแจ้ง"""
        user = User.query.get(session['user_id'])
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            category = request.form.get('category', 'equipment').strip()
            equipment_id = request.form.get('equipment_id', type=int)
            description = request.form.get('description', '').strip()
            contact_info = request.form.get('contact_info', '').strip()

            if not title or not description:
                flash('กรุณากรอกหัวข้อปัญหาและรายละเอียดปัญหาให้ครบถ้วน', 'danger')
                return redirect(url_for('user_issues'))

            # Handle Image Upload if attached
            image_path = None
            if 'image' in request.files:
                file = request.files['image']
                if file and file.filename != '' and allowed_file(file.filename):
                    filename = secure_filename(f"issue_{int(datetime.utcnow().timestamp())}_{file.filename}")
                    file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                    image_path = f"uploads/{filename}"

            report = IssueReport(
                user_id=user.user_id,
                equipment_id=equipment_id if equipment_id and equipment_id > 0 else None,
                title=title,
                category=category,
                description=description,
                contact_info=contact_info or user.phone_number or '',
                image_path=image_path,
                status='pending'
            )
            db.session.add(report)
            db.session.commit()

            # Create an in-app notification for the user to confirm receipt
            confirm_notif = Notification(
                user_id=user.user_id,
                title='บันทึกการรายงานปัญหาเรียบร้อยแล้ว',
                message=f'ระบบได้รับเรื่อง "{title}" ของคุณเรียบร้อยแล้ว เจ้าหน้าที่จะดำเนินการตรวจสอบโดยเร็ว',
                type='info',
                is_read=False
            )
            db.session.add(confirm_notif)
            db.session.commit()

            flash('ส่งรายงานปัญหาเรียบร้อยแล้ว เจ้าหน้าที่จะดำเนินการตรวจสอบโดยเร็วที่สุด', 'success')
            return redirect(url_for('user_issues'))

        # GET request
        my_issues = IssueReport.query.filter_by(user_id=user.user_id).order_by(IssueReport.created_at.desc()).all()
        equipment_list = Equipment.query.order_by(Equipment.name.asc()).all()

        return render_template(
            'issues.html',
            my_issues=my_issues,
            equipment_list=equipment_list,
            user=user,
            contact_info=get_issue_contact_info()
        )

    @app.route('/admin/issues')
    @roles_required('admin', 'staff')
    def admin_issues():
        """หน้าสำหรับเจ้าหน้าที่/Admin การตอบกลับปัญหาที่ผู้ใช้งานรายงานมา"""
        status_filter = request.args.get('status', 'all').strip()
        cat_filter = request.args.get('category', 'all').strip()
        search_q = request.args.get('q', '').strip()

        query = IssueReport.query.join(User, IssueReport.user_id == User.user_id)

        if status_filter != 'all':
            query = query.filter(IssueReport.status == status_filter)
        if cat_filter != 'all':
            query = query.filter(IssueReport.category == cat_filter)
        if search_q:
            query = query.filter(
                (IssueReport.title.ilike(f'%{search_q}%')) |
                (IssueReport.description.ilike(f'%{search_q}%')) |
                (User.first_name.ilike(f'%{search_q}%')) |
                (User.last_name.ilike(f'%{search_q}%')) |
                (User.student_or_citizen_id.ilike(f'%{search_q}%'))
            )

        issues = query.order_by(IssueReport.created_at.desc()).all()

        # Stats
        total_issues = IssueReport.query.count()
        pending_count = IssueReport.query.filter_by(status='pending').count()
        in_progress_count = IssueReport.query.filter_by(status='in_progress').count()
        resolved_count = IssueReport.query.filter_by(status='resolved').count()

        return render_template(
            'admin/issues.html',
            issues=issues,
            status_filter=status_filter,
            cat_filter=cat_filter,
            search_q=search_q,
            total_issues=total_issues,
            pending_count=pending_count,
            in_progress_count=in_progress_count,
            resolved_count=resolved_count,
            contact_info=get_issue_contact_info()
        )

    @app.route('/admin/issues/contact-info', methods=['POST'])
    @roles_required('admin', 'staff')
    def admin_issues_update_contact():
        """อัปเดตข้อมูลการติดต่อด่วนที่แสดงให้ผู้ใช้งานเห็นในหน้ารายงานปัญหา"""
        SystemSetting.set('contact_title', request.form.get('contact_title', '').strip(), 'หัวข้อติดต่อด่วน')
        SystemSetting.set('contact_location', request.form.get('contact_location', '').strip(), 'สถานที่ตั้งห้องพัสดุ')
        SystemSetting.set('contact_hours', request.form.get('contact_hours', '').strip(), 'เวลาให้บริการ')
        SystemSetting.set('contact_phone', request.form.get('contact_phone', '').strip(), 'เบอร์โทรศัพท์/โทรภายใน')
        SystemSetting.set('contact_line', request.form.get('contact_line', '').strip(), 'LINE / ช่องทางติดต่ออื่น')
        SystemSetting.set('contact_note', request.form.get('contact_note', '').strip(), 'หมายเหตุเพิ่มเติม')
        db.session.commit()
        flash('อัปเดตข้อมูลการติดต่อที่แสดงให้ผู้ใช้งานเห็นเรียบร้อยแล้ว', 'success')
        return redirect(url_for('admin_issues'))

    @app.route('/admin/issues/<int:report_id>/update', methods=['POST'])
    @roles_required('admin', 'staff')
    def admin_issue_update(report_id):
        """อัปเดตสถานะปัญหา และตอบกลับไปยังผู้แจ้ง"""
        issue = IssueReport.query.get_or_404(report_id)
        new_status = request.form.get('status', issue.status).strip()
        admin_response = request.form.get('admin_response', '').strip()
        staff_user = User.query.get(session['user_id'])

        issue.status = new_status
        issue.admin_response = admin_response
        if new_status in ['resolved', 'closed']:
            issue.resolved_by = staff_user.user_id

        db.session.commit()

        # Notify the reporter about the update
        status_labels = {
            'pending': 'รอดำเนินการ',
            'in_progress': 'กำลังตรวจสอบ',
            'resolved': 'แก้ไขแล้ว',
            'closed': 'ปิดงาน'
        }
        notif_msg = f'ปัญหาเรื่อง "{issue.title}" ได้รับการอัปเดตสถานะเป็น "{status_labels.get(new_status, new_status)}"'
        if admin_response:
            notif_msg += f'\nข้อความจากเจ้าหน้าที่: {admin_response}'

        reporter_notif = Notification(
            user_id=issue.user_id,
            title=f'อัปเดตรายงานปัญหา: {issue.title}',
            message=notif_msg,
            type='approval' if new_status == 'resolved' else 'info',
            is_read=False
        )
        db.session.add(reporter_notif)
        db.session.commit()

        flash(f'อัปเดตสถานะรายงานปัญหา #{issue.report_id} เรียบร้อยแล้ว พร้อมส่งการแจ้งเตือนไปยังผู้แจ้ง', 'success')
        return redirect(url_for('admin_issues'))

    @app.route('/admin/issues/<int:report_id>/delete', methods=['POST'])
    @roles_required('admin')
    def admin_issue_delete(report_id):
        """ลบรายการปัญหา (เฉพาะ Admin)"""
        issue = IssueReport.query.get_or_404(report_id)
        db.session.delete(issue)
        db.session.commit()
        flash(f'ลบรายงานปัญหา #{report_id} สำเร็จ', 'info')
        return redirect(url_for('admin_issues'))

    # -------------------------------------------------------------
    # REQUIREMENT: PURCHASE ORDERS & SUPPLIERS MANAGEMENT (การสั่งซื้อพัสดุและครุภัณฑ์)
    # -------------------------------------------------------------
    @app.route('/admin/purchases')
    @roles_required('admin', 'staff')
    def purchase_orders_list():
        status_filter = request.args.get('status', 'all')
        search_query = request.args.get('q', '').strip()

        query = PurchaseOrder.query
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        if search_query:
            query = query.join(Supplier).filter(
                (PurchaseOrder.po_number.ilike(f'%{search_query}%')) |
                (Supplier.company_name.ilike(f'%{search_query}%'))
            )

        orders = query.order_by(PurchaseOrder.order_date.desc()).all()

        total_orders_count = PurchaseOrder.query.count()
        pending_count = PurchaseOrder.query.filter_by(status='pending').count()
        received_count = PurchaseOrder.query.filter_by(status='received').count()
        total_spend = db.session.query(db.func.sum(PurchaseOrder.total_amount)).scalar() or 0.0
        suppliers_count = Supplier.query.count()

        return render_template(
            'admin/purchases.html',
            orders=orders,
            status_filter=status_filter,
            search_query=search_query,
            total_orders_count=total_orders_count,
            pending_count=pending_count,
            received_count=received_count,
            total_spend=total_spend,
            suppliers_count=suppliers_count
        )

    @app.route('/admin/purchases/new', methods=['GET', 'POST'])
    @roles_required('admin', 'staff')
    def purchase_order_new():
        if request.method == 'POST':
            supplier_id = request.form.get('supplier_id', type=int)
            po_number = request.form.get('po_number', '').strip()
            order_date_str = request.form.get('order_date')
            expected_date_str = request.form.get('expected_delivery_date')
            note = request.form.get('note', '').strip()

            if not supplier_id:
                flash('กรุณาเลือกบริษัทคู่ค้า / ผู้จัดจำหน่าย', 'danger')
                return redirect(url_for('purchase_order_new'))

            supplier = Supplier.query.get_or_404(supplier_id)

            # Auto-generate PO number if not provided or empty
            if not po_number:
                po_number = generate_next_po_number()

            # Check duplicate PO
            existing_po = PurchaseOrder.query.filter_by(po_number=po_number).first()
            if existing_po:
                po_number = generate_next_po_number()

            order_date = datetime.utcnow()
            if order_date_str:
                try:
                    order_date = datetime.strptime(order_date_str, '%Y-%m-%d')
                except ValueError:
                    order_date = datetime.utcnow()

            expected_delivery_date = None
            if expected_date_str:
                try:
                    expected_delivery_date = datetime.strptime(expected_date_str, '%Y-%m-%d')
                except ValueError:
                    expected_delivery_date = None

            # Parse items from form
            item_names = request.form.getlist('item_name[]')
            item_codes = request.form.getlist('item_code[]')
            quantities = request.form.getlist('quantity[]')
            units = request.form.getlist('unit[]')
            unit_prices = request.form.getlist('unit_price[]')
            equipment_ids = request.form.getlist('equipment_id[]')
            notes_list = request.form.getlist('notes[]')

            if not item_names or len(item_names) == 0:
                flash('กรุณาเพิ่มรายการวัสดุ/ครุภัณฑ์ที่ต้องการสั่งซื้ออย่างน้อย 1 รายการ', 'danger')
                return redirect(url_for('purchase_order_new', supplier_id=supplier_id))

            po = PurchaseOrder(
                po_number=po_number,
                supplier_id=supplier_id,
                order_date=order_date,
                expected_delivery_date=expected_delivery_date,
                total_amount=0.0,
                status='pending',
                note=note,
                created_by=session['user_id']
            )
            db.session.add(po)
            db.session.flush()

            grand_total = 0.0
            valid_items_count = 0
            for i in range(len(item_names)):
                name = item_names[i].strip()
                if not name:
                    continue
                code = item_codes[i].strip() if i < len(item_codes) else ''
                unit = units[i].strip() if i < len(units) and units[i].strip() else 'ชิ้น'
                try:
                    qty = int(quantities[i]) if i < len(quantities) else 1
                    qty = max(1, qty)
                except (ValueError, TypeError):
                    qty = 1
                try:
                    price = float(unit_prices[i]) if i < len(unit_prices) else 0.0
                    price = max(0.0, price)
                except (ValueError, TypeError):
                    price = 0.0

                eq_id = None
                if i < len(equipment_ids) and equipment_ids[i] and str(equipment_ids[i]).isdigit():
                    eq_id = int(equipment_ids[i])

                item_note = notes_list[i].strip() if i < len(notes_list) else ''

                line_total = qty * price
                grand_total += line_total

                po_item = PurchaseOrderItem(
                    po_id=po.po_id,
                    equipment_id=eq_id,
                    item_name=name,
                    item_code=code,
                    quantity=qty,
                    unit=unit,
                    unit_price=price,
                    total_price=line_total,
                    notes=item_note
                )
                db.session.add(po_item)
                valid_items_count += 1

            if valid_items_count == 0:
                db.session.rollback()
                flash('ไม่พบรายการสินค้าที่ระบุชื่อ กรุณากรอกชื่อสินค้าอย่างน้อย 1 รายการ', 'danger')
                return redirect(url_for('purchase_order_new', supplier_id=supplier_id))

            po.total_amount = grand_total
            db.session.commit()

            flash(f'สร้างใบสั่งซื้อ {po.po_number} สำหรับ {supplier.company_name} สำเร็จ! (รวม {valid_items_count} รายการ ยอดรวม ฿{grand_total:,.2f})', 'success')
            return redirect(url_for('purchase_order_detail', po_id=po.po_id))

        # GET request
        suppliers = Supplier.query.order_by(Supplier.company_name.asc()).all()
        selected_supplier_id = request.args.get('supplier_id', type=int)
        reorder_from_id = request.args.get('reorder_from', type=int)

        reorder_po = None
        if reorder_from_id:
            reorder_po = PurchaseOrder.query.get(reorder_from_id)
            if reorder_po and not selected_supplier_id:
                selected_supplier_id = reorder_po.supplier_id

        # Generate recommended PO number (Auto-number)
        suggested_po_number = generate_next_po_number()

        # Equipment list for system search
        all_equipment = Equipment.query.order_by(Equipment.name.asc()).all()

        # Recent purchase orders for reorder dropdown
        recent_pos = PurchaseOrder.query.order_by(PurchaseOrder.order_date.desc()).limit(15).all()

        return render_template(
            'admin/purchase_new.html',
            suppliers=suppliers,
            selected_supplier_id=selected_supplier_id,
            suggested_po_number=suggested_po_number,
            all_equipment=all_equipment,
            recent_pos=recent_pos,
            reorder_po=reorder_po,
            today_date=datetime.utcnow().strftime('%Y-%m-%d')
        )

    @app.route('/admin/purchases/<int:po_id>')
    @roles_required('admin', 'staff')
    def purchase_order_detail(po_id):
        po = PurchaseOrder.query.get_or_404(po_id)
        return render_template('admin/purchase_detail.html', po=po)

    @app.route('/admin/purchases/<int:po_id>/status', methods=['POST'])
    @roles_required('admin', 'staff')
    def purchase_order_update_status(po_id):
        po = PurchaseOrder.query.get_or_404(po_id)
        new_status = request.form.get('status')
        update_inventory = request.form.get('update_inventory') == '1'

        if new_status in ['pending', 'received', 'cancelled']:
            old_status = po.status
            po.status = new_status

            if new_status == 'received' and old_status != 'received' and update_inventory:
                staff_user = User.query.get(session['user_id'])
                receipt = GoodsReceipt(
                    po_id=po.po_id,
                    received_date=datetime.utcnow(),
                    status='completed',
                    received_by=staff_user.user_id
                )
                db.session.add(receipt)

                items_updated = 0
                for item in po.items:
                    if item.equipment_id:
                        eq = Equipment.query.get(item.equipment_id)
                        if eq:
                            eq.total_quantity += item.quantity
                            eq.available_quantity += item.quantity
                            if eq.status == 'borrowed' and eq.available_quantity > 0:
                                eq.status = 'available'
                            items_updated += 1
                flash(f'ปรับสถานะเป็น "ตรวจรับเข้าคลังแล้ว" และเพิ่มสต็อกพัสดุในระบบแล้ว ({items_updated} รายการ)', 'success')
            else:
                flash(f'ปรับสถานะใบสั่งซื้อ {po.po_number} เป็น "{po.status_display}" เรียบร้อยแล้ว', 'info')

            db.session.commit()

        return redirect(url_for('purchase_order_detail', po_id=po.po_id))

    # -------------------------------------------------------------
    # SUPPLIERS MANAGEMENT (ข้อมูลบริษัทคู่ค้า/ผู้จัดจำหน่าย และสินค้าที่ขาย)
    # -------------------------------------------------------------
    @app.route('/admin/suppliers')
    @roles_required('admin', 'staff')
    def suppliers_list():
        search_query = request.args.get('q', '').strip()
        query = Supplier.query
        if search_query:
            query = query.filter(
                (Supplier.company_name.ilike(f'%{search_query}%')) |
                (Supplier.contact_name.ilike(f'%{search_query}%')) |
                (Supplier.phone.ilike(f'%{search_query}%'))
            )
        suppliers = query.order_by(Supplier.company_name.asc()).all()
        categories = Category.query.all()
        next_product_code = generate_next_product_code()
        return render_template(
            'admin/suppliers.html',
            suppliers=suppliers,
            categories=categories,
            search_query=search_query,
            next_product_code=next_product_code
        )

    @app.route('/admin/suppliers/add', methods=['POST'])
    @roles_required('admin', 'staff')
    def supplier_add():
        company_name = request.form.get('company_name', '').strip()
        contact_name = request.form.get('contact_name', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        email = request.form.get('email', '').strip()
        tax_id = request.form.get('tax_id', '').strip()

        if not company_name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
                return jsonify({'success': False, 'message': 'กรุณาระบุชื่อบริษัท'}), 400
            flash('กรุณาระบุชื่อบริษัท', 'danger')
            return redirect(url_for('suppliers_list'))

        sup = Supplier(
            company_name=company_name,
            contact_name=contact_name,
            phone=phone,
            address=address,
            email=email,
            tax_id=tax_id
        )
        db.session.add(sup)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'supplier': sup.to_dict(), 'message': 'เพิ่มข้อมูลบริษัทเรียบร้อยแล้ว'})

        flash(f'เพิ่มบริษัทคู่ค้า "{sup.company_name}" สำเร็จ', 'success')
        return redirect(url_for('suppliers_list'))

    @app.route('/admin/suppliers/<int:supplier_id>/edit', methods=['POST'])
    @roles_required('admin', 'staff')
    def supplier_edit(supplier_id):
        sup = Supplier.query.get_or_404(supplier_id)
        company_name = request.form.get('company_name', '').strip()
        if company_name:
            sup.company_name = company_name
        sup.contact_name = request.form.get('contact_name', sup.contact_name or '').strip()
        sup.phone = request.form.get('phone', sup.phone or '').strip()
        sup.address = request.form.get('address', sup.address or '').strip()
        sup.email = request.form.get('email', sup.email or '').strip()
        sup.tax_id = request.form.get('tax_id', sup.tax_id or '').strip()

        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
            return jsonify({'success': True, 'supplier': sup.to_dict(), 'message': 'แก้ไขข้อมูลบริษัทเรียบร้อยแล้ว'})

        flash(f'แก้ไขข้อมูลบริษัท "{sup.company_name}" สำเร็จ', 'success')
        return redirect(request.referrer or url_for('suppliers_list'))

    @app.route('/admin/suppliers/<int:supplier_id>/products/add', methods=['POST'])
    @roles_required('admin', 'staff')
    def supplier_product_add(supplier_id):
        sup = Supplier.query.get_or_404(supplier_id)
        product_name = request.form.get('product_name', '').strip()
        product_code = request.form.get('product_code', '').strip()
        category_name = request.form.get('category_name', '').strip()
        unit = request.form.get('unit', 'ชิ้น').strip()
        unit_price = request.form.get('unit_price', 0.0, type=float)
        description = request.form.get('description', '').strip()
        equipment_id = request.form.get('equipment_id', type=int)

        if not product_name:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'message': 'กรุณาระบุชื่อสินค้า'}), 400
            flash('กรุณาระบุชื่อสินค้า', 'danger')
            return redirect(url_for('suppliers_list'))

        # Auto-number fallback if empty
        if not product_code:
            product_code = generate_next_product_code()

        prod = SupplierProduct(
            supplier_id=sup.supplier_id,
            equipment_id=equipment_id if equipment_id else None,
            product_name=product_name,
            product_code=product_code,
            category_name=category_name,
            unit=unit or 'ชิ้น',
            unit_price=unit_price,
            description=description
        )
        db.session.add(prod)
        db.session.commit()

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return jsonify({
                'success': True,
                'product': prod.to_dict(),
                'next_product_code': generate_next_product_code()
            })

        flash(f'เพิ่มสินค้า "{product_name}" ในแค็ตตาล็อกของ {sup.company_name} เรียบร้อยแล้ว', 'success')
        return redirect(request.referrer or url_for('suppliers_list'))

    # -------------------------------------------------------------
    # AJAX / JSON APIs FOR SEAMLESS DYNAMIC EXPERIENCE
    # -------------------------------------------------------------
    @app.route('/api/suppliers/<int:supplier_id>')
    @roles_required('admin', 'staff')
    def api_supplier_detail(supplier_id):
        sup = Supplier.query.get_or_404(supplier_id)
        return jsonify(sup.to_dict())

    @app.route('/api/suppliers/<int:supplier_id>/products')
    @roles_required('admin', 'staff')
    def api_supplier_products(supplier_id):
        sup = Supplier.query.get_or_404(supplier_id)
        products = [p.to_dict() for p in sup.products]
        return jsonify({
            'supplier': sup.to_dict(),
            'products': products
        })

    @app.route('/api/equipment/search')
    @roles_required('admin', 'staff')
    def api_equipment_search():
        q = request.args.get('q', '').strip()
        query = Equipment.query
        if q:
            query = query.filter(
                (Equipment.name.ilike(f'%{q}%')) |
                (Equipment.equipment_code.ilike(f'%{q}%'))
            )
        items = query.order_by(Equipment.name.asc()).limit(25).all()
        return jsonify([item.to_dict() for item in items])

    @app.route('/api/purchases/<int:po_id>/items')
    @roles_required('admin', 'staff')
    def api_purchase_items(po_id):
        po = PurchaseOrder.query.get_or_404(po_id)
        return jsonify({
            'po_id': po.po_id,
            'po_number': po.po_number,
            'supplier_id': po.supplier_id,
            'supplier_name': po.supplier.company_name,
            'total_amount': po.total_amount,
            'items': [item.to_dict() for item in po.items]
        })

    # -------------------------------------------------------------
    # DASHBOARD & REPORTS (ภาพรวมสถิติและรายงาน)
    # -------------------------------------------------------------
    @app.route('/admin/dashboard')
    @roles_required('admin', 'staff')
    def admin_dashboard():
        total_equipment = Equipment.query.count()
        total_items_qty = db.session.query(db.func.sum(Equipment.total_quantity)).scalar() or 0
        total_available_qty = db.session.query(db.func.sum(Equipment.available_quantity)).scalar() or 0
        active_borrows_count = Borrowing.query.filter(Borrowing.status.in_(['borrowed', 'overdue'])).count()
        pending_requests_count = BorrowRequest.query.filter_by(status='pending').count()
        overdue_count = Borrowing.query.filter_by(status='overdue').count()
        total_fines_revenue = db.session.query(db.func.sum(Fine.total_fine)).filter_by(payment_status='paid').scalar() or 0.0

        categories = Category.query.all()
        recent_requests = BorrowRequest.query.order_by(BorrowRequest.request_date.desc()).limit(5).all()
        recent_borrowings = Borrowing.query.order_by(Borrowing.borrow_date.desc()).limit(5).all()

        return render_template(
            'admin/dashboard.html',
            total_equipment=total_equipment,
            total_items_qty=total_items_qty,
            total_available_qty=total_available_qty,
            active_borrows_count=active_borrows_count,
            pending_requests_count=pending_requests_count,
            overdue_count=overdue_count,
            total_fines_revenue=total_fines_revenue,
            categories=categories,
            recent_requests=recent_requests,
            recent_borrowings=recent_borrowings
        )

    # -------------------------------------------------------------
    # GOODS RECEIVING — การรับเข้าวัสดุและครุภัณฑ์ใหม่
    # -------------------------------------------------------------
    @app.route('/admin/goods-receiving')
    @roles_required('admin', 'staff')
    def goods_receiving():
        """หน้าหลักรับเข้าวัสดุ/ครุภัณฑ์ + ประวัติการรับเข้า"""
        status_filter = request.args.get('status', 'all')
        type_filter = request.args.get('type', 'all')
        search_query = request.args.get('q', '').strip()

        query = GoodsReceipt.query
        if status_filter != 'all':
            query = query.filter_by(status=status_filter)
        if type_filter != 'all':
            query = query.filter_by(receipt_type=type_filter)
        if search_query:
            query = query.filter(
                (GoodsReceipt.receipt_number.ilike(f'%{search_query}%')) |
                (GoodsReceipt.supplier_name.ilike(f'%{search_query}%')) |
                (GoodsReceipt.document_ref.ilike(f'%{search_query}%'))
            )

        receipts = query.order_by(GoodsReceipt.received_date.desc()).all()

        # Stats
        total_receipts = GoodsReceipt.query.count()
        total_items_received = db.session.query(db.func.sum(GoodsReceipt.total_quantity)).scalar() or 0
        this_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0)
        month_receipts = GoodsReceipt.query.filter(GoodsReceipt.received_date >= this_month).count()

        # Pending POs for quick receive
        pending_pos = PurchaseOrder.query.filter_by(status='pending').order_by(PurchaseOrder.order_date.desc()).all()

        return render_template(
            'admin/goods_receiving.html',
            receipts=receipts,
            status_filter=status_filter,
            type_filter=type_filter,
            search_query=search_query,
            total_receipts=total_receipts,
            total_items_received=total_items_received,
            month_receipts=month_receipts,
            pending_pos=pending_pos
        )

    @app.route('/admin/goods-receiving/new', methods=['GET', 'POST'])
    @roles_required('admin', 'staff')
    def goods_receiving_new():
        """บันทึกการรับเข้าวัสดุ/ครุภัณฑ์ใหม่ (รับเข้าตรง)"""
        if request.method == 'POST':
            receipt_type = request.form.get('receipt_type', 'direct')
            supplier_name = request.form.get('supplier_name', '').strip()
            document_ref = request.form.get('document_ref', '').strip()
            note = request.form.get('note', '').strip()
            received_date_str = request.form.get('received_date', '')

            # Parse received date
            if received_date_str:
                try:
                    received_date = datetime.strptime(received_date_str, '%Y-%m-%d')
                except ValueError:
                    received_date = datetime.utcnow()
            else:
                received_date = datetime.utcnow()

            # Auto-generate receipt number
            receipt_number = generate_next_receipt_number(receipt_type)

            staff_user = User.query.get(session['user_id'])

            receipt = GoodsReceipt(
                receipt_number=receipt_number,
                receipt_type=receipt_type,
                supplier_name=supplier_name or None,
                received_date=received_date,
                status='completed',
                note=note or None,
                document_ref=document_ref or None,
                received_by=staff_user.user_id
            )
            db.session.add(receipt)
            db.session.flush()

            # Parse items
            item_names = request.form.getlist('item_name[]')
            item_codes = request.form.getlist('item_code[]')
            quantities = request.form.getlist('quantity[]')
            units = request.form.getlist('unit[]')
            conditions = request.form.getlist('condition[]')
            equipment_ids = request.form.getlist('equipment_id[]')
            item_notes = request.form.getlist('item_note[]')

            total_items_count = 0
            total_qty = 0
            items_updated = 0

            for i in range(len(item_names)):
                name = item_names[i].strip() if i < len(item_names) else ''
                if not name:
                    continue

                code = item_codes[i].strip() if i < len(item_codes) else ''
                unit = units[i].strip() if i < len(units) and units[i].strip() else 'ชิ้น'
                condition = conditions[i] if i < len(conditions) else 'new'
                item_note = item_notes[i].strip() if i < len(item_notes) else ''

                try:
                    qty = max(1, int(quantities[i])) if i < len(quantities) else 1
                except (ValueError, TypeError):
                    qty = 1

                eq_id = None
                if i < len(equipment_ids) and equipment_ids[i] and str(equipment_ids[i]).isdigit():
                    eq_id = int(equipment_ids[i])

                # Create receipt item
                ri = GoodsReceiptItem(
                    receipt_id=receipt.receipt_id,
                    equipment_id=eq_id,
                    item_name=name,
                    item_code=code,
                    quantity=qty,
                    unit=unit,
                    condition=condition,
                    note=item_note or None,
                    inventory_updated=False
                )
                db.session.add(ri)

                # Auto-update equipment quantity
                if eq_id:
                    eq = Equipment.query.get(eq_id)
                    if eq:
                        eq.total_quantity += qty
                        eq.available_quantity += qty
                        if eq.status in ['borrowed', 'maintenance', 'damaged'] and eq.available_quantity > 0:
                            eq.status = 'available'
                        ri.inventory_updated = True
                        items_updated += 1

                total_items_count += 1
                total_qty += qty

            if total_items_count == 0:
                db.session.rollback()
                flash('กรุณาเพิ่มรายการวัสดุ/ครุภัณฑ์อย่างน้อย 1 รายการ', 'danger')
                return redirect(url_for('goods_receiving_new'))

            receipt.total_items = total_items_count
            receipt.total_quantity = total_qty
            db.session.commit()

            flash(
                f'บันทึกการรับเข้าเลขที่ {receipt.receipt_number} สำเร็จ! '
                f'({total_items_count} รายการ รวม {total_qty} ชิ้น'
                f'{f", อัปเดตสต็อก {items_updated} รายการ" if items_updated else ""})',
                'success'
            )
            return redirect(url_for('goods_receiving_detail', receipt_id=receipt.receipt_id))

        # GET — render form
        equipment_list = Equipment.query.order_by(Equipment.name.asc()).all()
        categories = Category.query.order_by(Category.category_name.asc()).all()
        locations = Location.query.order_by(Location.location_name.asc()).all()
        suppliers = Supplier.query.order_by(Supplier.company_name.asc()).all()

        return render_template(
            'admin/goods_receiving_new.html',
            equipment_list=equipment_list,
            categories=categories,
            locations=locations,
            suppliers=suppliers,
            today_date=datetime.utcnow().strftime('%Y-%m-%d')
        )

    @app.route('/admin/goods-receiving/from-po/<int:po_id>', methods=['POST'])
    @roles_required('admin', 'staff')
    def goods_receiving_from_po(po_id):
        """รับเข้าจากใบสั่งซื้อ (PO) — อัปเดตสต็อกอัตโนมัติ"""
        po = PurchaseOrder.query.get_or_404(po_id)
        if po.status == 'received':
            flash('ใบสั่งซื้อนี้ได้รับการตรวจรับเข้าคลังแล้ว', 'warning')
            return redirect(url_for('goods_receiving'))

        staff_user = User.query.get(session['user_id'])

        # Auto-generate receipt number
        receipt_number = generate_next_receipt_number('purchase')

        receipt = GoodsReceipt(
            receipt_number=receipt_number,
            po_id=po.po_id,
            receipt_type='purchase',
            supplier_name=po.supplier.company_name,
            received_date=datetime.utcnow(),
            status='completed',
            note=f'รับเข้าจากใบสั่งซื้อ {po.po_number}',
            document_ref=po.po_number,
            received_by=staff_user.user_id
        )
        db.session.add(receipt)
        db.session.flush()

        total_items = 0
        total_qty = 0
        items_updated = 0

        for po_item in po.items:
            ri = GoodsReceiptItem(
                receipt_id=receipt.receipt_id,
                equipment_id=po_item.equipment_id,
                item_name=po_item.item_name,
                item_code=po_item.item_code,
                quantity=po_item.quantity,
                unit=po_item.unit,
                condition='new',
                inventory_updated=False
            )
            db.session.add(ri)

            if po_item.equipment_id:
                eq = Equipment.query.get(po_item.equipment_id)
                if eq:
                    eq.total_quantity += po_item.quantity
                    eq.available_quantity += po_item.quantity
                    if eq.status in ['borrowed', 'maintenance', 'damaged'] and eq.available_quantity > 0:
                        eq.status = 'available'
                    ri.inventory_updated = True
                    items_updated += 1

            total_items += 1
            total_qty += po_item.quantity

        receipt.total_items = total_items
        receipt.total_quantity = total_qty

        # Update PO status
        po.status = 'received'
        db.session.commit()

        flash(
            f'ตรวจรับเข้าคลังจาก PO {po.po_number} สำเร็จ! '
            f'(เลขที่ใบรับ: {receipt.receipt_number}, {total_items} รายการ, อัปเดตสต็อก {items_updated} รายการ)',
            'success'
        )
        return redirect(url_for('goods_receiving_detail', receipt_id=receipt.receipt_id))

    @app.route('/admin/goods-receiving/<int:receipt_id>')
    @roles_required('admin', 'staff')
    def goods_receiving_detail(receipt_id):
        """ดูรายละเอียดใบรับเข้าวัสดุ/ครุภัณฑ์"""
        receipt = GoodsReceipt.query.get_or_404(receipt_id)
        return render_template('admin/goods_receiving_detail.html', receipt=receipt)

    @app.route('/admin/goods-receiving/<int:receipt_id>/delete', methods=['POST'])
    @roles_required('admin')
    def goods_receiving_delete(receipt_id):
        """ลบใบรับเข้า พร้อม rollback สต็อกที่อัปเดตไปแล้ว"""
        receipt = GoodsReceipt.query.get_or_404(receipt_id)
        receipt_number = receipt.receipt_number

        try:
            # Rollback inventory for items that were updated
            rollback_count = 0
            for item in receipt.items:
                if item.inventory_updated and item.equipment_id:
                    eq = Equipment.query.get(item.equipment_id)
                    if eq:
                        eq.total_quantity = max(0, eq.total_quantity - item.quantity)
                        eq.available_quantity = max(0, eq.available_quantity - item.quantity)
                        if eq.available_quantity == 0 and eq.total_quantity > 0:
                            eq.status = 'borrowed'
                        rollback_count += 1

            # If receipt was from PO, revert PO status back to pending
            if receipt.po_id and receipt.purchase_order:
                receipt.purchase_order.status = 'pending'

            db.session.delete(receipt)
            db.session.commit()

            msg = f'ลบใบรับเข้าเลขที่ {receipt_number} เรียบร้อยแล้ว'
            if rollback_count > 0:
                msg += f' (คืนค่าสต็อก {rollback_count} รายการ)'
            flash(msg, 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'เกิดข้อผิดพลาดในการลบใบรับเข้า: {str(e)}', 'danger')

        return redirect(url_for('goods_receiving'))

    @app.route('/admin/goods-receiving/<int:receipt_id>/print')
    @roles_required('admin', 'staff')
    def goods_receiving_print(receipt_id):
        """พิมพ์ใบรับเข้าวัสดุ/ครุภัณฑ์ (เอกสารทางการ)"""
        receipt = GoodsReceipt.query.get_or_404(receipt_id)
        return render_template('admin/goods_receiving_print.html', receipt=receipt)

    @app.route('/api/equipment/create', methods=['POST'])
    @roles_required('admin', 'staff')
    def api_equipment_create():
        """สร้างรายการครุภัณฑ์ใหม่ผ่าน AJAX (ใช้จากหน้ารับเข้า)"""
        data = request.get_json() if request.is_json else request.form
        code = (data.get('equipment_code') or '').strip()
        name = (data.get('name') or '').strip()
        category_id = data.get('category_id', type=int) if hasattr(data, 'get') else None
        location_id = data.get('location_id', type=int) if hasattr(data, 'get') else None
        description = (data.get('description') or '').strip()

        if request.is_json:
            try:
                category_id = int(data.get('category_id', 0)) if data.get('category_id') else None
                location_id = int(data.get('location_id', 0)) if data.get('location_id') else None
            except (ValueError, TypeError):
                category_id = None
                location_id = None

        if not name:
            return jsonify({'success': False, 'message': 'กรุณาระบุชื่อรายการ'}), 400

        if not category_id or not location_id:
            return jsonify({'success': False, 'message': 'กรุณาเลือกหมวดหมู่และสถานที่จัดเก็บ'}), 400

        if not code:
            code = generate_next_equipment_code()
        elif Equipment.query.filter_by(equipment_code=code).first():
            return jsonify({'success': False, 'message': f'รหัสพัสดุ/ครุภัณฑ์ {code} มีอยู่ในระบบแล้ว'}), 400

        eq = Equipment(
            equipment_code=code,
            name=name,
            category_id=category_id,
            location_id=location_id,
            total_quantity=0,
            available_quantity=0,
            status='available',
            description=description
        )
        db.session.add(eq)
        db.session.commit()

        return jsonify({
            'success': True,
            'equipment': eq.to_dict(),
            'message': f'สร้างรายการ {name} ({code}) สำเร็จ'
        })

    return app

if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        db.create_all()
    print("ระบบยืม-คืนวัสดุและครุภัณฑ์ วิทยาลัยการอาชีพหนองหาน พร้อมทำงานที่ http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
