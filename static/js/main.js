// Minimalist UI JavaScript Handlers

document.addEventListener('DOMContentLoaded', () => {
    // 0. Update Mobile Subbar Current Date (e.g. 23 Oct 2026)
    const mobileDateEl = document.getElementById('mobileCurrentDate');
    if (mobileDateEl) {
        const today = new Date();
        const options = { day: 'numeric', month: 'short', year: 'numeric' };
        mobileDateEl.textContent = today.toLocaleDateString('en-GB', options);
    }

    // 1. Flash alert dismiss
    document.querySelectorAll('.alert-close').forEach(btn => {
        btn.addEventListener('click', () => {
            btn.closest('.alert').style.display = 'none';
        });
    });

    // Auto-hide success alerts after 6 seconds
    setTimeout(() => {
        document.querySelectorAll('.alert-success').forEach(el => {
            el.style.transition = 'opacity 0.4s ease';
            el.style.opacity = '0';
            setTimeout(() => el.remove(), 400);
        });
    }, 6000);

    // 2. Escape key closes any open modal
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') {
            document.querySelectorAll('.modal-backdrop.active').forEach(modal => {
                closeModal(modal.id);
            });
        }
    });

    // 3. Close modal when clicking on backdrop
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', (e) => {
            if (e.target === backdrop) {
                closeModal(backdrop.id);
            }
        });
    });

    // 4. Image Upload Preview Handler
    document.querySelectorAll('input[type="file"][data-preview]').forEach(input => {
        const previewTargetId = input.getAttribute('data-preview');
        const previewImg = document.getElementById(previewTargetId);
        if (previewImg) {
            input.addEventListener('change', () => {
                const file = input.files[0];
                if (file) {
                    const reader = new FileReader();
                    reader.onload = (e) => {
                        previewImg.src = e.target.result;
                        previewImg.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                }
            });
        }
    });

    // 5. Sidebar Toggle & Responsive Navigation Handlers
    const sidebar = document.getElementById('appSidebar');
    const backdrop = document.getElementById('sidebarBackdrop');
    const toggleBtn = document.getElementById('sidebarToggle');
    const closeBtn = document.getElementById('sidebarCloseBtn');
    const collapseBtn = document.getElementById('sidebarCollapseBtn');
    const bottomNavMenuBtn = document.getElementById('bottomNavMenuToggle');

    function openSidebar() {
        if (sidebar) sidebar.classList.add('open');
        if (backdrop) backdrop.classList.add('active');
        document.body.style.overflow = 'hidden';
    }

    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('open');
        if (backdrop) backdrop.classList.remove('active');
        document.body.style.overflow = '';
    }

    if (toggleBtn) toggleBtn.addEventListener('click', openSidebar);
    if (bottomNavMenuBtn) bottomNavMenuBtn.addEventListener('click', openSidebar);
    if (closeBtn) closeBtn.addEventListener('click', closeSidebar);
    if (backdrop) backdrop.addEventListener('click', closeSidebar);

    // Close mobile drawer when a link is clicked
    if (sidebar) {
        sidebar.querySelectorAll('.sidebar-link').forEach(link => {
            link.addEventListener('click', () => {
                if (window.innerWidth < 1024) {
                    closeSidebar();
                }
            });
        });
    }

    // Desktop Sidebar Collapse with LocalStorage preference
    if (collapseBtn && sidebar) {
        // Restore saved preference on load for wide screens
        const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
        if (isCollapsed && window.innerWidth >= 1024) {
            sidebar.classList.add('collapsed');
        }

        collapseBtn.addEventListener('click', () => {
            sidebar.classList.toggle('collapsed');
            const nowCollapsed = sidebar.classList.contains('collapsed');
            localStorage.setItem('sidebarCollapsed', nowCollapsed);
        });
    }

    // 6. Guest Mobile Menu Toggle Handler
    const guestMenuToggle = document.getElementById('guestMenuToggle');
    const guestMobileMenu = document.getElementById('guestMobileMenu');
    if (guestMenuToggle && guestMobileMenu) {
        guestMenuToggle.addEventListener('click', () => {
            guestMobileMenu.classList.toggle('open');
        });
    }
});

// Modal helpers
function openModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
        document.body.style.overflow = 'hidden';
    }
}

function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
        document.body.style.overflow = '';
    }
}

// Open Borrow Modal for User
function prepareBorrowModal(equipmentId, equipmentName, equipmentCode, availableQty, imagePath) {
    document.getElementById('borrowEquipmentId').value = equipmentId;
    document.getElementById('borrowItemName').innerText = equipmentName;
    document.getElementById('borrowItemCode').innerText = equipmentCode;
    document.getElementById('borrowMaxQtyText').innerText = availableQty;
    
    const qtyInput = document.getElementById('borrowQuantityInput');
    if (qtyInput) {
        qtyInput.max = availableQty;
        qtyInput.value = 1;
    }

    const imgEl = document.getElementById('borrowItemImage');
    if (imgEl) {
        imgEl.src = imagePath ? `/static/${imagePath}` : '/static/uploads/multimeter.svg';
    }

    // Set default expected date to 3 days from now
    const returnDateInput = document.getElementById('borrowReturnDate');
    if (returnDateInput) {
        const d = new Date();
        d.setDate(d.getDate() + 3);
        const yyyy = d.getFullYear();
        const mm = String(d.getMonth() + 1).padStart(2, '0');
        const dd = String(d.getDate()).padStart(2, '0');
        returnDateInput.value = `${yyyy}-${mm}-${dd}`;
        returnDateInput.min = new Date().toISOString().split('T')[0];
    }

    openModal('borrowModal');
}

// Open Reject Modal for Staff (Requirement 2)
function prepareRejectModal(requestId, applicantName, equipmentName) {
    const form = document.getElementById('rejectForm');
    form.action = `/admin/requests/${requestId}/reject`;
    document.getElementById('rejectApplicantName').innerText = applicantName;
    document.getElementById('rejectEquipmentName').innerText = equipmentName;
    document.getElementById('rejectReasonInput').value = '';
    openModal('rejectModal');
}

// Open Return Modal for Staff
function prepareReturnModal(borrowId, borrowerName, equipmentName, borrowDate, dueDate, isOverdue, daysLate, estimatedFine) {
    document.getElementById('returnBorrowId').value = borrowId;
    document.getElementById('returnBorrowerName').innerText = borrowerName;
    document.getElementById('returnEquipmentName').innerText = equipmentName;
    document.getElementById('returnBorrowDate').innerText = borrowDate;
    document.getElementById('returnDueDate').innerText = dueDate;

    const overdueAlert = document.getElementById('returnOverdueAlert');
    const lateDaysText = document.getElementById('returnLateDaysText');
    const lateFineText = document.getElementById('returnLateFineText');
    const damageFineInput = document.getElementById('returnDamageFineInput');
    const totalFineDisplay = document.getElementById('returnTotalFineDisplay');

    if (isOverdue) {
        overdueAlert.style.display = 'block';
        lateDaysText.innerText = daysLate;
        lateFineText.innerText = estimatedFine.toLocaleString('th-TH', { minimumFractionDigits: 2 });
    } else {
        overdueAlert.style.display = 'none';
        lateFineText.innerText = '0.00';
    }

    function updateTotal() {
        const damage = parseFloat(damageFineInput.value) || 0;
        const total = (isOverdue ? estimatedFine : 0) + damage;
        totalFineDisplay.innerText = total.toLocaleString('th-TH', { minimumFractionDigits: 2 }) + ' บาท';
    }

    if (damageFineInput) {
        damageFineInput.value = '0';
        damageFineInput.oninput = updateTotal;
    }
    updateTotal();

    openModal('returnModal');
}
