from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = 'users'
    user_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    student_or_citizen_id = db.Column(db.String(20), nullable=False)
    first_name = db.Column(db.String(100), nullable=False)
    last_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), default='student', nullable=False)  # 'student', 'teacher', 'staff', 'admin'
    line_user_id = db.Column(db.String(100), nullable=True)
    department = db.Column(db.String(100), nullable=True, default='แผนกวิชาช่างอิเล็กทรอนิกส์')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    borrow_requests = db.relationship('BorrowRequest', foreign_keys='BorrowRequest.user_id', backref='user', lazy=True)
    borrowings = db.relationship('Borrowing', foreign_keys='Borrowing.user_id', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True, order_by='Notification.created_at.desc()')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        if not self.password_hash:
            return False
        try:
            return check_password_hash(self.password_hash, password)
        except Exception:
            return False

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @property
    def role_display(self):
        roles = {
            'student': 'นักเรียน/นักศึกษา',
            'teacher': 'อาจารย์/ครูผู้สอน',
            'staff': 'เจ้าหน้าที่พัสดุ',
            'admin': 'ผู้ดูแลระบบ'
        }
        return roles.get(self.role, self.role)

    @property
    def role_badge_class(self):
        badges = {
            'student': 'badge-info',
            'teacher': 'badge-primary',
            'staff': 'badge-warning',
            'admin': 'badge-danger'
        }
        return badges.get(self.role, 'badge-secondary')


class Category(db.Model):
    __tablename__ = 'categories'
    category_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    category_name = db.Column(db.String(100), nullable=False)
    type = db.Column(db.String(20), default='durable_goods', nullable=False)  # 'material', 'durable_goods'

    # Relationships
    equipment_list = db.relationship('Equipment', backref='category', lazy=True)

    @property
    def type_display(self):
        return 'วัสดุ (ใช้หมดไป)' if self.type == 'material' else 'ครุภัณฑ์ (คงทนถาวร)'


class Location(db.Model):
    __tablename__ = 'locations'
    location_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    location_name = db.Column(db.String(150), nullable=False)
    description = db.Column(db.String(255), nullable=True)

    # Relationships
    equipment_list = db.relationship('Equipment', backref='location', lazy=True)


class FineRate(db.Model):
    __tablename__ = 'fine_rates'
    fine_rate_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rate_type = db.Column(db.String(50), nullable=False)  # 'late_return', 'damage', 'loss'
    amount_per_day = db.Column(db.Float, default=100.0, nullable=False)
    description = db.Column(db.String(255), nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Supplier(db.Model):
    __tablename__ = 'suppliers'
    supplier_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    company_name = db.Column(db.String(150), nullable=False)
    contact_name = db.Column(db.String(100), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(255), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    purchase_orders = db.relationship('PurchaseOrder', backref='supplier', lazy=True)
    products = db.relationship('SupplierProduct', backref='supplier', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'supplier_id': self.supplier_id,
            'company_name': self.company_name,
            'contact_name': self.contact_name or '',
            'phone': self.phone or '',
            'address': self.address or '',
            'email': self.email or '',
            'tax_id': self.tax_id or ''
        }


class SupplierProduct(db.Model):
    __tablename__ = 'supplier_products'
    product_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.equipment_id'), nullable=True)
    product_name = db.Column(db.String(150), nullable=False)
    product_code = db.Column(db.String(50), nullable=True)
    category_name = db.Column(db.String(100), nullable=True)
    unit = db.Column(db.String(30), default='ชิ้น')
    unit_price = db.Column(db.Float, default=0.0)
    description = db.Column(db.String(255), nullable=True)

    equipment = db.relationship('Equipment', backref='supplier_products')

    def to_dict(self):
        return {
            'product_id': self.product_id,
            'supplier_id': self.supplier_id,
            'equipment_id': self.equipment_id,
            'product_name': self.product_name,
            'product_code': self.product_code or '',
            'category_name': self.category_name or '',
            'unit': self.unit or 'ชิ้น',
            'unit_price': self.unit_price,
            'description': self.description or ''
        }


class Equipment(db.Model):
    __tablename__ = 'equipment'
    equipment_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_code = db.Column(db.String(50), unique=True, nullable=False)
    name = db.Column(db.String(150), nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.category_id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.location_id'), nullable=False)
    total_quantity = db.Column(db.Integer, default=1, nullable=False)
    available_quantity = db.Column(db.Integer, default=1, nullable=False)
    status = db.Column(db.String(20), default='available', nullable=False)  # 'available', 'borrowed', 'maintenance', 'damaged'
    image_path = db.Column(db.String(255), nullable=True)
    description = db.Column(db.Text, nullable=True)

    # Relationships
    borrow_requests = db.relationship('BorrowRequest', backref='equipment', lazy=True)
    borrowings = db.relationship('Borrowing', backref='equipment', lazy=True)
    maintenances = db.relationship('Maintenance', backref='equipment', lazy=True)

    @property
    def status_display(self):
        mapping = {
            'available': 'พร้อมใช้งาน',
            'borrowed': 'ถูกยืมทั้งหมด',
            'maintenance': 'ส่งซ่อมบำรุง',
            'damaged': 'ชำรุดเสียหาย'
        }
        return mapping.get(self.status, self.status)

    @property
    def status_badge_class(self):
        mapping = {
            'available': 'badge-success',
            'borrowed': 'badge-warning',
            'maintenance': 'badge-info',
            'damaged': 'badge-danger'
        }
        return mapping.get(self.status, 'badge-secondary')

    def to_dict(self):
        return {
            'equipment_id': self.equipment_id,
            'equipment_code': self.equipment_code,
            'name': self.name,
            'category_name': self.category.category_name if self.category else '',
            'category_type': self.category.type if self.category else 'durable_goods',
            'available_quantity': self.available_quantity,
            'total_quantity': self.total_quantity,
            'status': self.status,
            'image_path': self.image_path
        }


class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_orders'
    po_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('suppliers.supplier_id'), nullable=False)
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.DateTime, nullable=True)
    total_amount = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # 'pending', 'received', 'cancelled'
    note = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    creator = db.relationship('User', foreign_keys=[created_by], backref='created_pos')
    items = db.relationship('PurchaseOrderItem', backref='purchase_order', lazy=True, cascade='all, delete-orphan')

    @property
    def status_display(self):
        mapping = {
            'pending': 'รอรับพัสดุ',
            'received': 'ตรวจรับเข้าคลังแล้ว',
            'cancelled': 'ยกเลิกคำสั่งซื้อ'
        }
        return mapping.get(self.status, self.status)

    @property
    def status_badge_class(self):
        mapping = {
            'pending': 'badge-warning',
            'received': 'badge-success',
            'cancelled': 'badge-danger'
        }
        return mapping.get(self.status, 'badge-secondary')

    @property
    def items_count(self):
        return sum(item.quantity for item in self.items)


class PurchaseOrderItem(db.Model):
    __tablename__ = 'purchase_order_items'
    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.po_id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.equipment_id'), nullable=True)
    item_name = db.Column(db.String(150), nullable=False)
    item_code = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit = db.Column(db.String(30), default='ชิ้น')
    unit_price = db.Column(db.Float, default=0.0, nullable=False)
    total_price = db.Column(db.Float, default=0.0, nullable=False)
    notes = db.Column(db.String(255), nullable=True)

    equipment = db.relationship('Equipment', backref='po_items')

    def to_dict(self):
        return {
            'item_id': self.item_id,
            'equipment_id': self.equipment_id,
            'item_name': self.item_name,
            'item_code': self.item_code or '',
            'quantity': self.quantity,
            'unit': self.unit or 'ชิ้น',
            'unit_price': self.unit_price,
            'total_price': self.total_price,
            'notes': self.notes or ''
        }


class GoodsReceipt(db.Model):
    __tablename__ = 'goods_receipts'
    receipt_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    po_id = db.Column(db.Integer, db.ForeignKey('purchase_orders.po_id'), nullable=True)  # nullable: รับเข้าตรงไม่ผ่าน PO ได้
    receipt_type = db.Column(db.String(20), default='purchase')  # 'purchase' (จาก PO), 'direct' (รับเข้าตรง), 'donation' (รับบริจาค), 'transfer' (โอนย้าย)
    supplier_name = db.Column(db.String(150), nullable=True)  # สำหรับ direct receipt
    received_date = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='completed')  # 'completed', 'claim_pending'
    note = db.Column(db.Text, nullable=True)
    document_ref = db.Column(db.String(100), nullable=True)  # เลขที่เอกสารอ้างอิง
    total_items = db.Column(db.Integer, default=0)
    total_quantity = db.Column(db.Integer, default=0)
    received_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    purchase_order = db.relationship('PurchaseOrder', backref='goods_receipts')
    receiver = db.relationship('User', foreign_keys=[received_by], backref='received_goods')
    items = db.relationship('GoodsReceiptItem', backref='goods_receipt', lazy=True, cascade='all, delete-orphan')

    @property
    def receipt_type_display(self):
        mapping = {
            'purchase': '📦 รับจากใบสั่งซื้อ (PO)',
            'direct': '📥 รับเข้าตรง',
            'donation': '🎁 รับบริจาค',
            'transfer': '🔄 โอนย้ายเข้า'
        }
        return mapping.get(self.receipt_type, self.receipt_type)

    @property
    def receipt_type_short(self):
        mapping = {
            'purchase': 'จาก PO',
            'direct': 'รับเข้าตรง',
            'donation': 'รับบริจาค',
            'transfer': 'โอนย้าย'
        }
        return mapping.get(self.receipt_type, self.receipt_type)

    @property
    def receipt_type_badge(self):
        mapping = {
            'purchase': 'badge-primary',
            'direct': 'badge-success',
            'donation': 'badge-info',
            'transfer': 'badge-warning'
        }
        return mapping.get(self.receipt_type, 'badge-secondary')


class GoodsReceiptItem(db.Model):
    __tablename__ = 'goods_receipt_items'
    item_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    receipt_id = db.Column(db.Integer, db.ForeignKey('goods_receipts.receipt_id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.equipment_id'), nullable=True)
    item_name = db.Column(db.String(150), nullable=False)
    item_code = db.Column(db.String(50), nullable=True)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    unit = db.Column(db.String(30), default='ชิ้น')
    condition = db.Column(db.String(20), default='new')  # 'new', 'used', 'refurbished'
    note = db.Column(db.String(255), nullable=True)
    inventory_updated = db.Column(db.Boolean, default=False)  # ทำเครื่องหมายว่าอัปเดตสต็อกแล้ว

    equipment = db.relationship('Equipment', backref='receipt_items')

    @property
    def condition_display(self):
        mapping = {
            'new': 'ใหม่',
            'used': 'มือสอง',
            'refurbished': 'ซ่อมแซมแล้ว'
        }
        return mapping.get(self.condition, self.condition)



class BorrowRequest(db.Model):
    __tablename__ = 'borrow_requests'
    request_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.equipment_id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    purpose = db.Column(db.String(255), nullable=True)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_return_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # 'pending', 'approved', 'rejected'
    rejection_reason = db.Column(db.String(255), nullable=True)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=True)

    approver = db.relationship('User', foreign_keys=[approved_by], backref='approved_requests')
    borrowing = db.relationship('Borrowing', backref='borrow_request', uselist=False, lazy=True)

    @property
    def status_display(self):
        mapping = {
            'pending': 'รออนุมัติ',
            'approved': 'อนุมัติแล้ว',
            'rejected': 'ไม่อนุมัติ'
        }
        return mapping.get(self.status, self.status)

    @property
    def status_badge_class(self):
        mapping = {
            'pending': 'badge-warning',
            'approved': 'badge-success',
            'rejected': 'badge-danger'
        }
        return mapping.get(self.status, 'badge-secondary')


class Borrowing(db.Model):
    __tablename__ = 'borrowings'
    borrow_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    request_id = db.Column(db.Integer, db.ForeignKey('borrow_requests.request_id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.equipment_id'), nullable=False)
    quantity = db.Column(db.Integer, default=1, nullable=False)
    borrow_date = db.Column(db.DateTime, default=datetime.utcnow)
    due_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='borrowed', nullable=False)  # 'borrowed', 'returned', 'overdue'

    return_record = db.relationship('ReturnRecord', backref='borrowing', uselist=False, lazy=True)

    @property
    def is_overdue(self):
        if self.status == 'borrowed' and datetime.utcnow() > self.due_date:
            return True
        return self.status == 'overdue'

    @property
    def status_display(self):
        if self.status == 'borrowed' and datetime.utcnow() > self.due_date:
            return 'เกินกำหนดคืน'
        mapping = {
            'borrowed': 'กำลังยืม',
            'returned': 'คืนแล้ว',
            'overdue': 'เกินกำหนดคืน'
        }
        return mapping.get(self.status, self.status)

    @property
    def status_badge_class(self):
        if self.status == 'borrowed' and datetime.utcnow() > self.due_date:
            return 'badge-danger'
        mapping = {
            'borrowed': 'badge-primary',
            'returned': 'badge-success',
            'overdue': 'badge-danger'
        }
        return mapping.get(self.status, 'badge-secondary')


class ReturnRecord(db.Model):
    __tablename__ = 'returns'
    return_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    borrow_id = db.Column(db.Integer, db.ForeignKey('borrowings.borrow_id'), nullable=False)
    return_date = db.Column(db.DateTime, default=datetime.utcnow)
    condition_status = db.Column(db.String(20), default='normal', nullable=False)  # 'normal', 'damaged', 'lost'
    late_days = db.Column(db.Integer, default=0)
    received_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    receiver = db.relationship('User', foreign_keys=[received_by], backref='received_returns')
    fine = db.relationship('Fine', backref='return_record', uselist=False, lazy=True)

    @property
    def condition_display(self):
        mapping = {
            'normal': 'สภาพปกติสมบูรณ์',
            'damaged': 'ชำรุดเสียหาย',
            'lost': 'สูญหาย'
        }
        return mapping.get(self.condition_status, self.condition_status)


class Fine(db.Model):
    __tablename__ = 'fines'
    fine_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    return_id = db.Column(db.Integer, db.ForeignKey('returns.return_id'), nullable=False)
    receipt_number = db.Column(db.String(50), unique=True, nullable=False)
    late_fine = db.Column(db.Float, default=0.0)
    damage_fine = db.Column(db.Float, default=0.0)
    total_fine = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), default='cash')  # 'cash', 'transfer'
    payment_status = db.Column(db.String(20), default='unpaid')  # 'unpaid', 'paid'
    paid_at = db.Column(db.DateTime, nullable=True)
    issued_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    issuer = db.relationship('User', foreign_keys=[issued_by], backref='issued_fines')

    @property
    def status_display(self):
        return 'ชำระแล้ว' if self.payment_status == 'paid' else 'ค้างชำระ'

    @property
    def status_badge_class(self):
        return 'badge-success' if self.payment_status == 'paid' else 'badge-danger'


class Maintenance(db.Model):
    __tablename__ = 'maintenances'
    maintenance_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    equipment_id = db.Column(db.Integer, db.ForeignKey('equipment.equipment_id'), nullable=False)
    issue_description = db.Column(db.String(255), nullable=False)
    cost = db.Column(db.Float, default=0.0)
    maintenance_date = db.Column(db.DateTime, default=datetime.utcnow)
    completion_date = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='in_repair')  # 'in_repair', 'repaired', 'scrapped'
    recorded_by = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)

    recorder = db.relationship('User', foreign_keys=[recorded_by], backref='recorded_maintenances')

    @property
    def status_display(self):
        mapping = {
            'in_repair': 'กำลังส่งซ่อม',
            'repaired': 'ซ่อมเสร็จสิ้น',
            'scrapped': 'ตัดจำหน่าย/ซ่อมไม่ได้'
        }
        return mapping.get(self.status, self.status)


class Notification(db.Model):
    __tablename__ = 'notifications'
    notification_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(50), default='system')  # 'approval', 'rejection', 'due_soon', 'overdue', 'info'
    channel = db.Column(db.String(50), default='system')  # 'system', 'line', 'email'
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @property
    def icon(self):
        icons = {
            'approval': 'check-circle',
            'rejection': 'x-circle',
            'due_soon': 'clock',
            'overdue': 'alert-triangle',
            'info': 'bell'
        }
        return icons.get(self.type, 'bell')
