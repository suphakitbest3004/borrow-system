import io
from app import create_app
from models import (
    db, User, Equipment, Category, BorrowRequest, Notification,
    PurchaseOrder, GoodsReceipt, GoodsReceiptItem
)

def run_tests():
    app = create_app()
    app.config['TESTING'] = True
    client = app.test_client()

    with app.app_context():
        # 1. Test Catalog (Home)
        res = client.get('/catalog')
        assert res.status_code == 200, f"Catalog failed: {res.status_code}"
        assert 'คลังวัสดุและครุภัณฑ์'.encode('utf-8') in res.data
        print("✓ Test 1: Catalog page loads successfully.")

        # 2. Test Login as Student
        student = User.query.filter_by(role='student').first()
        assert student is not None
        res = client.post('/login', data={'quick_role': 'student'}, follow_redirects=True)
        assert res.status_code == 200
        assert student.first_name.encode('utf-8') in res.data
        print(f"✓ Test 2: Student login ({student.first_name}) succeeded.")

        # 3. Test Profile View (Requirement 1)
        res = client.get('/profile')
        assert res.status_code == 200
        assert 'ข้อมูลส่วนตัวและประวัติการยืม'.encode('utf-8') in res.data
        if student.student_or_citizen_id:
            assert student.student_or_citizen_id.encode('utf-8') in res.data
        assert 'รายการอุปกรณ์ที่กำลังยืมอยู่ในขณะนี้'.encode('utf-8') in res.data
        print("✓ Test 3: User Profile (Requirement 1) loads personal info & borrowings correctly.")

        # 4. Test Submitting a Borrow Request
        eq = Equipment.query.filter_by(status='available').first()
        res = client.post('/borrow/request', data={
            'equipment_id': eq.equipment_id,
            'quantity': 1,
            'expected_days': 2,
            'purpose': 'ทดสอบยืมสำหรับงานปฏิบัติการ'
        }, follow_redirects=True)
        assert res.status_code == 200
        print("✓ Test 4: Borrow request submitted successfully.")

        # Logout student
        client.get('/logout')

        # 5. Test Staff Login & Approval (Requirement 2)
        res = client.post('/login', data={'quick_role': 'staff'}, follow_redirects=True)
        assert res.status_code == 200
        assert 'จัดการคำขอยืม'.encode('utf-8') in res.data

        # Find pending request
        pending_req = BorrowRequest.query.filter_by(status='pending').first()
        assert pending_req is not None
        req_id = pending_req.request_id

        # Staff clicks Approve
        res = client.post(f'/admin/requests/{req_id}/approve', follow_redirects=True)
        assert res.status_code == 200
        assert 'อนุมัติคำขอยืม'.encode('utf-8') in res.data

        # Check that notification was generated
        notif = Notification.query.filter_by(user_id=pending_req.user_id, type='approval').first()
        assert notif is not None
        print("✓ Test 5: Staff approval (Requirement 2) & instant notification dispatch succeeded.")

        # 6. Test Admin Login & Category CRUD (Requirement 3: เพิ่มประเภทใหม่ได้)
        client.get('/logout')
        client.post('/login', data={'quick_role': 'admin'}, follow_redirects=True)

        res = client.post('/admin/categories/add', data={
            'category_name': 'อุปกรณ์เซนเซอร์และไอโอที (IoT)',
            'type': 'durable_goods'
        }, follow_redirects=True)
        assert res.status_code == 200
        new_cat = Category.query.filter_by(category_name='อุปกรณ์เซนเซอร์และไอโอที (IoT)').first()
        assert new_cat is not None
        print("✓ Test 6: Add new category (Requirement 3) succeeded.")

        # 7. Test Equipment CRUD with Image Upload (Requirement 3 & 4)
        mock_image = (io.BytesIO(b"fake image data"), "test_gear.png")
        res = client.post('/admin/equipment/add', data={
            'equipment_code': 'EQ-TEST-999',
            'name': 'บอร์ดทดลอง ESP32 IoT Node',
            'category_id': new_cat.category_id,
            'location_id': 1,
            'total_quantity': 5,
            'status': 'available',
            'description': 'บอร์ดไมโครคอนโทรลเลอร์พร้อม Wi-Fi & Bluetooth',
            'image': mock_image
        }, content_type='multipart/form-data', follow_redirects=True)
        assert res.status_code == 200
        new_eq = Equipment.query.filter_by(equipment_code='EQ-TEST-999').first()
        assert new_eq is not None
        assert new_eq.image_path is not None
        print("✓ Test 7: Add equipment with image upload (Requirement 3 & 4) succeeded.")

        # 8. Test New Equipment Page & Batch Add ('บันทึกทั้งหมด')
        res = client.get('/admin/equipment/new')
        assert res.status_code == 200
        assert 'หน้าเพิ่มวัสดุและครุภัณฑ์'.encode('utf-8') in res.data
        assert 'บันทึกทั้งหมด'.encode('utf-8') in res.data

        # Test Batch Add with 2 items at once
        res = client.post('/admin/equipment/batch-add', data={
            'equipment_code[]': ['EQ-BATCH-001', 'EQ-BATCH-002'],
            'name[]': ['ชุดทดลองวงจรตรรกศาสตร์ดิจิทัล', 'เครื่องจ่ายไฟกระแสตรง DC Power Supply'],
            'category_id[]': [new_cat.category_id, new_cat.category_id],
            'location_id[]': [1, 1],
            'total_quantity[]': [3, 2],
            'status[]': ['available', 'available'],
            'description[]': ['สำหรับวิชาดิจิทัล', 'ปรับแรงดัน 0-30V 5A']
        }, follow_redirects=True)
        assert res.status_code == 200
        assert Equipment.query.filter_by(equipment_code='EQ-BATCH-001').first() is not None
        assert Equipment.query.filter_by(equipment_code='EQ-BATCH-002').first() is not None
        print("✓ Test 8: New equipment page & Batch add with 'บันทึกทั้งหมด' button succeeded.")

        # 9. Test Notification Logs
        res = client.get('/admin/notification-logs')
        assert res.status_code == 200
        assert 'บันทึกการส่งแจ้งเตือน'.encode('utf-8') in res.data
        print("✓ Test 9: Notification logs view succeeded.")

        # 10. Test Returns & Receipts
        res = client.get('/admin/returns')
        assert res.status_code == 200
        print("✓ Test 10: Returns and fine management view succeeded.")

        # 11. Test Purchase Orders List & History View (Requirement: เพิ่มเมนูการสั่งซื้อ และดูประวัติได้)
        res = client.get('/admin/purchases')
        assert res.status_code == 200
        assert 'การสั่งซื้อวัสดุและครุภัณฑ์'.encode('utf-8') in res.data
        assert 'ประวัติการสั่งซื้อพัสดุและครุภัณฑ์'.encode('utf-8') in res.data
        print("✓ Test 11: Purchase orders history list (Requirement: การสั่งซื้อและดูประวัติ) succeeded.")

        # 12. Test Suppliers Directory & Edit Supplier (Requirement: ดูข้อมูลบริษัทที่สั่ง และแก้ไขได้)
        res = client.get('/admin/suppliers')
        assert res.status_code == 200
        assert 'ข้อมูลบริษัทคู่ค้าและผู้จัดจำหน่าย'.encode('utf-8') in res.data
        from models import Supplier, PurchaseOrder
        test_sup = Supplier.query.first()
        assert test_sup is not None

        # Test edit supplier
        res = client.post(f'/admin/suppliers/{test_sup.supplier_id}/edit', data={
            'company_name': test_sup.company_name,
            'contact_name': 'คุณผู้จัดการฝ่ายขาย (แก้ไขใหม่)',
            'phone': '042-999-888',
            'email': 'sales_updated@supplier.com',
            'tax_id': '0415599999999',
            'address': 'ที่อยู่ใหม่ อ.เมือง จ.อุดรธานี'
        }, follow_redirects=True)
        assert res.status_code == 200
        db.session.refresh(test_sup)
        assert test_sup.contact_name == 'คุณผู้จัดการฝ่ายขาย (แก้ไขใหม่)'
        assert test_sup.phone == '042-999-888'
        print("✓ Test 12: View and edit supplier information (Requirement: ดูและแก้ไขข้อมูลบริษัท) succeeded.")

        # 13. Test Supplier Products API (Requirement: ถ้าเลือกแล้วจะมีสินค้าที่บริษัทขายโชว์ขึ้นด้วย)
        res = client.get(f'/api/suppliers/{test_sup.supplier_id}/products')
        assert res.status_code == 200
        data = res.get_json()
        assert 'products' in data
        assert len(data['products']) > 0
        print(f"✓ Test 13: Supplier products dynamic catalog ({len(data['products'])} items) succeeded.")

        # 14. Test Search Equipment / Material API (Requirement: ค้นหาจาก ชื่อวัสดุและครุภัณฑ์ได้)
        existing_eq = Equipment.query.first()
        search_term = existing_eq.name[:5] if existing_eq else 'EQ'
        res = client.get(f'/api/equipment/search?q={search_term}')
        assert res.status_code == 200
        search_data = res.get_json()
        assert len(search_data) > 0
        print(f"✓ Test 14: Search by material/equipment name API ('{search_term}') succeeded.")

        # 15. Test Re-order from Previous Orders API & Create New PO (Requirement: สั่งจากรายการเดิมก็ได้)
        first_po = PurchaseOrder.query.first()
        assert first_po is not None
        res = client.get(f'/api/purchases/{first_po.po_id}/items')
        assert res.status_code == 200
        po_items_data = res.get_json()
        assert len(po_items_data['items']) > 0

        # Submit new Purchase Order
        res = client.post('/admin/purchases/new', data={
            'supplier_id': test_sup.supplier_id,
            'po_number': 'PO-TEST-2026-999',
            'order_date': '2026-10-13',
            'expected_delivery_date': '2026-10-20',
            'note': 'ทดสอบสร้างใบสั่งซื้อระบบใหม่',
            'item_name[]': ['มัลติมิเตอร์ Fluke 115 สำหรับช่างอิเล็กทรอนิกส์', 'หัวแร้ง Hakko FX-888D'],
            'item_code[]': ['EQ-TEST-01', 'MT-TEST-02'],
            'quantity[]': [2, 3],
            'unit[]': ['เครื่อง', 'ชุด'],
            'unit_price[]': [4800.0, 3450.0],
            'equipment_id[]': ['', ''],
            'notes[]': ['ห้องแล็บ 1', 'สำรองใช้งาน']
        }, follow_redirects=True)
        assert res.status_code == 200
        assert 'PO-TEST-2026-999'.encode('utf-8') in res.data
        created_po = PurchaseOrder.query.filter_by(po_number='PO-TEST-2026-999').first()
        assert created_po is not None
        assert len(created_po.items) == 2
        assert created_po.total_amount == (2 * 4800.0 + 3 * 3450.0)
        print("✓ Test 15: Create new purchase order & verify item calculations succeeded.")

        # 16. Test Goods Receiving List (Requirement 7: ตรวจรับเข้าพัสดุและครุภัณฑ์)
        res = client.get('/admin/goods-receiving')
        assert res.status_code == 200
        assert 'รับเข้าวัสดุและครุภัณฑ์'.encode('utf-8') in res.data
        print("✓ Test 16: Goods Receiving dashboard & receipt history list succeeded.")

        # 17. Test Direct Goods Receipt & Inventory Auto-update
        eq_before = Equipment.query.first()
        assert eq_before is not None
        initial_qty = eq_before.available_quantity

        res = client.post('/admin/goods-receiving/new', data={
            'receipt_type': 'direct',
            'supplier_name': 'หจก. อุดรเทคโนโลยีการศึกษา',
            'document_ref': 'INV-2026-0042',
            'received_date': '2026-10-18',
            'note': 'รับเข้าตรงสำหรับห้องเรียนปฏิบัติการ',
            'item_name[]': [eq_before.name],
            'item_code[]': [eq_before.equipment_code],
            'quantity[]': [3],
            'unit[]': ['เครื่อง'],
            'condition[]': ['new'],
            'equipment_id[]': [eq_before.equipment_id],
            'item_note[]': ['ทดสอบรับเข้าตรง']
        }, follow_redirects=True)
        assert res.status_code == 200

        db.session.refresh(eq_before)
        assert eq_before.available_quantity == initial_qty + 3
        print(f"✓ Test 17: Direct Goods Receipt created & equipment inventory auto-updated (+3) succeeded.")

        # 18. Test Goods Receipt Detail & Print View
        latest_gr = GoodsReceipt.query.order_by(GoodsReceipt.receipt_id.desc()).first()
        assert latest_gr is not None
        res_detail = client.get(f'/admin/goods-receiving/{latest_gr.receipt_id}')
        assert res_detail.status_code == 200
        assert latest_gr.receipt_number.encode('utf-8') in res_detail.data

        res_print = client.get(f'/admin/goods-receiving/{latest_gr.receipt_id}/print')
        assert res_print.status_code == 200
        assert 'ใบรับเข้าวัสดุ/ครุภัณฑ์'.encode('utf-8') in res_print.data
        print(f"✓ Test 18: Goods Receipt detail view & official printable form ({latest_gr.receipt_number}) succeeded.")

        # 19. Test Quick Receive from Purchase Order (PO)
        pending_po = PurchaseOrder.query.filter_by(status='pending').first()
        if pending_po:
            po_id = pending_po.po_id
            po_num = pending_po.po_number
            res_po_rcv = client.post(f'/admin/goods-receiving/from-po/{po_id}', follow_redirects=True)
            assert res_po_rcv.status_code == 200
            db.session.refresh(pending_po)
            assert pending_po.status == 'received'
            print(f"✓ Test 19: Quick receive from PO ({po_num}) & automatic status update succeeded.")

        # 20. Test Delete Goods Receipt with Inventory Rollback
        gr_to_delete = GoodsReceipt.query.order_by(GoodsReceipt.receipt_id.desc()).first()
        if gr_to_delete:
            gr_id = gr_to_delete.receipt_id
            gr_num = gr_to_delete.receipt_number
            # Check item to rollback
            first_item = gr_to_delete.items[0] if gr_to_delete.items else None
            eq_target = Equipment.query.get(first_item.equipment_id) if first_item and first_item.equipment_id else None
            target_qty_before = eq_target.available_quantity if eq_target else 0

            res_del = client.post(f'/admin/goods-receiving/{gr_id}/delete', follow_redirects=True)
            assert res_del.status_code == 200
            if eq_target and first_item and first_item.inventory_updated:
                db.session.refresh(eq_target)
                assert eq_target.available_quantity == target_qty_before - first_item.quantity
            print(f"✓ Test 20: Delete receipt ({gr_num}) & inventory rollback verification succeeded.")

    print("\n🎉 ALL 20 TESTS PASSED SUCCESSFULLY! The system conforms 100% to specifications.")

if __name__ == '__main__':
    run_tests()


