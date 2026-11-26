-- Schema for the Flask/SQLAlchemy inventory application.
-- Import this file in phpMyAdmin. It creates tables only; no sample records are included.
CREATE DATABASE IF NOT EXISTS `nonghan_borrow_db`
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `nonghan_borrow_db`;

CREATE TABLE `users` (
  `user_id` INT NOT NULL AUTO_INCREMENT,
  `student_or_citizen_id` VARCHAR(20) NOT NULL,
  `first_name` VARCHAR(100) NOT NULL,
  `last_name` VARCHAR(100) NOT NULL,
  `email` VARCHAR(100) NOT NULL,
  `password_hash` VARCHAR(255) NOT NULL,
  `phone_number` VARCHAR(20) NULL,
  `role` VARCHAR(20) NOT NULL DEFAULT 'student',
  `line_user_id` VARCHAR(100) NULL,
  `department` VARCHAR(100) NULL DEFAULT 'แผนกวิชาช่างอิเล็กทรอนิกส์',
  `created_at` DATETIME NULL,
  PRIMARY KEY (`user_id`), UNIQUE KEY `uq_users_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `categories` (
  `category_id` INT NOT NULL AUTO_INCREMENT,
  `category_name` VARCHAR(100) NOT NULL,
  `type` VARCHAR(20) NOT NULL DEFAULT 'durable_goods',
  PRIMARY KEY (`category_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `locations` (
  `location_id` INT NOT NULL AUTO_INCREMENT,
  `location_name` VARCHAR(150) NOT NULL,
  `description` VARCHAR(255) NULL,
  PRIMARY KEY (`location_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `fine_rates` (
  `fine_rate_id` INT NOT NULL AUTO_INCREMENT,
  `rate_type` VARCHAR(50) NOT NULL,
  `amount_per_day` FLOAT NOT NULL DEFAULT 100.0,
  `description` VARCHAR(255) NULL,
  `updated_at` DATETIME NULL,
  PRIMARY KEY (`fine_rate_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `suppliers` (
  `supplier_id` INT NOT NULL AUTO_INCREMENT,
  `company_name` VARCHAR(150) NOT NULL,
  `contact_name` VARCHAR(100) NULL,
  `phone` VARCHAR(20) NULL,
  `address` VARCHAR(255) NULL,
  `email` VARCHAR(100) NULL,
  `tax_id` VARCHAR(50) NULL,
  `created_at` DATETIME NULL,
  PRIMARY KEY (`supplier_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `equipment` (
  `equipment_id` INT NOT NULL AUTO_INCREMENT,
  `equipment_code` VARCHAR(50) NOT NULL,
  `name` VARCHAR(150) NOT NULL,
  `category_id` INT NOT NULL,
  `location_id` INT NOT NULL,
  `total_quantity` INT NOT NULL DEFAULT 1,
  `available_quantity` INT NOT NULL DEFAULT 1,
  `status` VARCHAR(20) NOT NULL DEFAULT 'available',
  `image_path` VARCHAR(255) NULL,
  `description` TEXT NULL,
  PRIMARY KEY (`equipment_id`), UNIQUE KEY `uq_equipment_code` (`equipment_code`),
  CONSTRAINT `fk_equipment_category` FOREIGN KEY (`category_id`) REFERENCES `categories` (`category_id`),
  CONSTRAINT `fk_equipment_location` FOREIGN KEY (`location_id`) REFERENCES `locations` (`location_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `supplier_products` (
  `product_id` INT NOT NULL AUTO_INCREMENT,
  `supplier_id` INT NOT NULL,
  `equipment_id` INT NULL,
  `product_name` VARCHAR(150) NOT NULL,
  `product_code` VARCHAR(50) NULL,
  `category_name` VARCHAR(100) NULL,
  `unit` VARCHAR(30) NULL DEFAULT 'ชิ้น',
  `unit_price` FLOAT NULL DEFAULT 0.0,
  `description` VARCHAR(255) NULL,
  PRIMARY KEY (`product_id`),
  CONSTRAINT `fk_supplier_products_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`),
  CONSTRAINT `fk_supplier_products_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `purchase_orders` (
  `po_id` INT NOT NULL AUTO_INCREMENT,
  `po_number` VARCHAR(50) NOT NULL,
  `supplier_id` INT NOT NULL,
  `order_date` DATETIME NULL,
  `expected_delivery_date` DATETIME NULL,
  `total_amount` FLOAT NULL DEFAULT 0.0,
  `status` VARCHAR(20) NULL DEFAULT 'pending',
  `note` TEXT NULL,
  `created_by` INT NOT NULL,
  PRIMARY KEY (`po_id`), UNIQUE KEY `uq_purchase_orders_po_number` (`po_number`),
  CONSTRAINT `fk_purchase_orders_supplier` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`supplier_id`),
  CONSTRAINT `fk_purchase_orders_creator` FOREIGN KEY (`created_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `purchase_order_items` (
  `item_id` INT NOT NULL AUTO_INCREMENT,
  `po_id` INT NOT NULL,
  `equipment_id` INT NULL,
  `item_name` VARCHAR(150) NOT NULL,
  `item_code` VARCHAR(50) NULL,
  `quantity` INT NOT NULL DEFAULT 1,
  `unit` VARCHAR(30) NULL DEFAULT 'ชิ้น',
  `unit_price` FLOAT NOT NULL DEFAULT 0.0,
  `total_price` FLOAT NOT NULL DEFAULT 0.0,
  `notes` VARCHAR(255) NULL,
  PRIMARY KEY (`item_id`),
  CONSTRAINT `fk_po_items_po` FOREIGN KEY (`po_id`) REFERENCES `purchase_orders` (`po_id`),
  CONSTRAINT `fk_po_items_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `goods_receipts` (
  `receipt_id` INT NOT NULL AUTO_INCREMENT,
  `receipt_number` VARCHAR(50) NOT NULL,
  `po_id` INT NULL,
  `receipt_type` VARCHAR(20) NULL DEFAULT 'purchase',
  `supplier_name` VARCHAR(150) NULL,
  `received_date` DATETIME NULL,
  `status` VARCHAR(20) NULL DEFAULT 'completed',
  `note` TEXT NULL,
  `document_ref` VARCHAR(100) NULL,
  `total_items` INT NULL DEFAULT 0,
  `total_quantity` INT NULL DEFAULT 0,
  `received_by` INT NOT NULL,
  PRIMARY KEY (`receipt_id`), UNIQUE KEY `uq_goods_receipts_receipt_number` (`receipt_number`),
  CONSTRAINT `fk_goods_receipts_po` FOREIGN KEY (`po_id`) REFERENCES `purchase_orders` (`po_id`),
  CONSTRAINT `fk_goods_receipts_receiver` FOREIGN KEY (`received_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `goods_receipt_items` (
  `item_id` INT NOT NULL AUTO_INCREMENT,
  `receipt_id` INT NOT NULL,
  `equipment_id` INT NULL,
  `item_name` VARCHAR(150) NOT NULL,
  `item_code` VARCHAR(50) NULL,
  `quantity` INT NULL DEFAULT 1,
  `unit` VARCHAR(30) NULL DEFAULT 'ชิ้น',
  `condition` VARCHAR(20) NULL DEFAULT 'new',
  `note` VARCHAR(255) NULL,
  `inventory_updated` BOOL NULL DEFAULT 0,
  PRIMARY KEY (`item_id`),
  CONSTRAINT `fk_receipt_items_receipt` FOREIGN KEY (`receipt_id`) REFERENCES `goods_receipts` (`receipt_id`),
  CONSTRAINT `fk_receipt_items_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `borrow_requests` (
  `request_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `equipment_id` INT NOT NULL,
  `quantity` INT NOT NULL DEFAULT 1,
  `purpose` VARCHAR(255) NULL,
  `request_date` DATETIME NULL,
  `expected_return_date` DATETIME NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'pending',
  `rejection_reason` VARCHAR(255) NULL,
  `approved_by` INT NULL,
  PRIMARY KEY (`request_id`),
  CONSTRAINT `fk_borrow_requests_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_borrow_requests_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`),
  CONSTRAINT `fk_borrow_requests_approver` FOREIGN KEY (`approved_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `borrowings` (
  `borrow_id` INT NOT NULL AUTO_INCREMENT,
  `request_id` INT NOT NULL,
  `user_id` INT NOT NULL,
  `equipment_id` INT NOT NULL,
  `quantity` INT NOT NULL DEFAULT 1,
  `borrow_date` DATETIME NULL,
  `due_date` DATETIME NOT NULL,
  `status` VARCHAR(20) NOT NULL DEFAULT 'borrowed',
  PRIMARY KEY (`borrow_id`),
  CONSTRAINT `fk_borrowings_request` FOREIGN KEY (`request_id`) REFERENCES `borrow_requests` (`request_id`),
  CONSTRAINT `fk_borrowings_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `fk_borrowings_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `returns` (
  `return_id` INT NOT NULL AUTO_INCREMENT,
  `borrow_id` INT NOT NULL,
  `return_date` DATETIME NULL,
  `condition_status` VARCHAR(20) NOT NULL DEFAULT 'normal',
  `late_days` INT NULL DEFAULT 0,
  `received_by` INT NOT NULL,
  PRIMARY KEY (`return_id`),
  CONSTRAINT `fk_returns_borrowing` FOREIGN KEY (`borrow_id`) REFERENCES `borrowings` (`borrow_id`),
  CONSTRAINT `fk_returns_receiver` FOREIGN KEY (`received_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `fines` (
  `fine_id` INT NOT NULL AUTO_INCREMENT,
  `return_id` INT NOT NULL,
  `receipt_number` VARCHAR(50) NOT NULL,
  `late_fine` FLOAT NULL DEFAULT 0.0,
  `damage_fine` FLOAT NULL DEFAULT 0.0,
  `total_fine` FLOAT NULL DEFAULT 0.0,
  `payment_method` VARCHAR(20) NULL DEFAULT 'cash',
  `payment_status` VARCHAR(20) NULL DEFAULT 'unpaid',
  `paid_at` DATETIME NULL,
  `issued_by` INT NOT NULL,
  PRIMARY KEY (`fine_id`), UNIQUE KEY `uq_fines_receipt_number` (`receipt_number`),
  CONSTRAINT `fk_fines_return` FOREIGN KEY (`return_id`) REFERENCES `returns` (`return_id`),
  CONSTRAINT `fk_fines_issuer` FOREIGN KEY (`issued_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `maintenances` (
  `maintenance_id` INT NOT NULL AUTO_INCREMENT,
  `equipment_id` INT NOT NULL,
  `issue_description` VARCHAR(255) NOT NULL,
  `cost` FLOAT NULL DEFAULT 0.0,
  `maintenance_date` DATETIME NULL,
  `completion_date` DATETIME NULL,
  `status` VARCHAR(20) NULL DEFAULT 'in_repair',
  `recorded_by` INT NOT NULL,
  PRIMARY KEY (`maintenance_id`),
  CONSTRAINT `fk_maintenances_equipment` FOREIGN KEY (`equipment_id`) REFERENCES `equipment` (`equipment_id`),
  CONSTRAINT `fk_maintenances_recorder` FOREIGN KEY (`recorded_by`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE `notifications` (
  `notification_id` INT NOT NULL AUTO_INCREMENT,
  `user_id` INT NOT NULL,
  `title` VARCHAR(150) NOT NULL,
  `message` TEXT NOT NULL,
  `type` VARCHAR(50) NULL DEFAULT 'system',
  `channel` VARCHAR(50) NULL DEFAULT 'system',
  `is_read` BOOL NULL DEFAULT 0,
  `created_at` DATETIME NULL,
  PRIMARY KEY (`notification_id`),
  CONSTRAINT `fk_notifications_user` FOREIGN KEY (`user_id`) REFERENCES `users` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
