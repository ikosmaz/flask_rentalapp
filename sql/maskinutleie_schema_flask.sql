-- Machinerental_flask database

DROP DATABASE IF EXISTS machinerental_flask;
CREATE DATABASE machinerental_flask CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
USE machinerental_flask;

-- ==========================
-- Tables
-- ==========================

CREATE TABLE city (
  postnr CHAR(4) NOT NULL PRIMARY KEY,
  city VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE address (
  address_id INT AUTO_INCREMENT PRIMARY KEY,
  street VARCHAR(100) NOT NULL,
  gatenr CHAR(4) NOT NULL,
  city_postnr CHAR(4) NOT NULL,
  
  CONSTRAINT fk_city_postnr FOREIGN KEY (city_postnr)
        REFERENCES city(postnr)
) ENGINE=InnoDB;

CREATE TABLE customer (
  customer_id INT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  type ENUM('Privat','Bedrift') NOT NULL,
  email VARCHAR(255),
  invoice_address_id INT NOT NULL,
  delivery_address_id INT NOT NULL,
  
  CONSTRAINT fk_cust_invoice_address FOREIGN KEY (invoice_address_id)
    REFERENCES address(address_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  CONSTRAINT fk_cust_delivery_address FOREIGN KEY (delivery_address_id)
    REFERENCES address(address_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

CREATE TABLE customer_phone (
  phone VARCHAR(20) NOT NULL,
  customer_id INT NOT NULL,  
  
  PRIMARY KEY (customer_id, phone),
  CONSTRAINT fk_phone_customer FOREIGN KEY (customer_id)
    REFERENCES customer(customer_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;

CREATE TABLE employee (
  employee_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(200) NOT NULL,
  phone VARCHAR(20)
) ENGINE=InnoDB;

  CREATE TABLE employee_login (
    employee_id INT PRIMARY KEY,
    username VARCHAR(100) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','user') NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    CONSTRAINT fk_login_employee FOREIGN KEY (employee_id)
      REFERENCES employee(employee_id)
      ON UPDATE CASCADE ON DELETE CASCADE
  ) ENGINE=InnoDB;

CREATE TABLE equipment_category (
  category_id INT PRIMARY KEY,
  category ENUM('Lette maskiner','Tunge maskiner','Annleggsutstyr') NOT NULL
) ENGINE=InnoDB;

CREATE TABLE equipment_model (
  model_id INT PRIMARY KEY,
  type VARCHAR(100) NOT NULL,
  brand VARCHAR(100) NOT NULL,
  model VARCHAR(100) NOT NULL,
  description LONGTEXT,
  daily_price DECIMAL(6,2) NOT NULL,
  total_quantity INT NOT NULL,
  quantity_in_stock INT DEFAULT 0,
  equipment_category_id INT NOT NULL,
  
  UNIQUE KEY uk_model (type, brand, model),
  CONSTRAINT fk_equipment_category_id FOREIGN KEY (equipment_category_id)
        REFERENCES equipment_category(category_id)
) ENGINE=InnoDB;


CREATE TABLE equipment_instance (
  model_id INT NOT NULL,
  instans_nr INT NOT NULL,
  last_maintenance DATE,
  next_maintenance DATE,
  
  PRIMARY KEY (model_id, instans_nr),
  CONSTRAINT fk_instance_model FOREIGN KEY (model_id)
    REFERENCES equipment_model(model_id)
    ON UPDATE CASCADE ON DELETE CASCADE
) ENGINE=InnoDB;


CREATE TABLE rental (
  rental_id INT AUTO_INCREMENT PRIMARY KEY,
  customer_id INT NOT NULL,
  model_id INT NOT NULL,
  instans_nr INT NOT NULL,
  rent_date DATE NOT NULL,
  return_date DATE NULL,
  payment_method ENUM('Kort','Kontant','Vipps','Giro') NOT NULL,
  employee_id INT NOT NULL,
  deliver_to_customer BOOLEAN NOT NULL DEFAULT FALSE,
  delivery_cost DECIMAL(10,2) NOT NULL DEFAULT 0,
  
  UNIQUE KEY uk_rental_natural (
    customer_id, model_id, instans_nr, rent_date),

  -- Identifying FK-s
  CONSTRAINT fk_rental_customer FOREIGN KEY (customer_id)
    REFERENCES customer(customer_id)
    ON UPDATE CASCADE ON DELETE RESTRICT,

  CONSTRAINT fk_rental_instance FOREIGN KEY (model_id, instans_nr)
    REFERENCES equipment_instance(model_id, instans_nr)
    ON UPDATE CASCADE ON DELETE RESTRICT,
  
  CONSTRAINT fk_rental_employee FOREIGN KEY (employee_id)
    REFERENCES employee(employee_id)
    ON UPDATE CASCADE ON DELETE RESTRICT
) ENGINE=InnoDB;

-- ==========================
-- Calculations
-- ==========================

DELIMITER $$

CREATE PROCEDURE update_stock(IN p_model_id INT)
BEGIN
    UPDATE equipment_model em
    SET quantity_in_stock = em.total_quantity -
        (
            SELECT COUNT(*)
            FROM rental r
            WHERE r.model_id = em.model_id
            AND r.return_date IS NULL
        )
    WHERE em.model_id = p_model_id;
END$$

DELIMITER ;

DELIMITER $$
CREATE TRIGGER trg_rental_after_insert
AFTER INSERT ON rental
FOR EACH ROW
BEGIN
    CALL update_stock(NEW.model_id);
END$$

CREATE TRIGGER trg_rental_after_update
AFTER UPDATE ON rental
FOR EACH ROW
BEGIN
    CALL update_stock(NEW.model_id);
END$$

CREATE TRIGGER trg_rental_after_delete
AFTER DELETE ON rental
FOR EACH ROW
BEGIN
    CALL update_stock(OLD.model_id);
END$$

DELIMITER ;

-- ==========================
-- Data
-- ==========================
INSERT INTO city (postnr, city) VALUES
  ('8501','Narvik'),
  ('8500','Narvik'),
  ('8001','Bodø'),
  ('8000','Bodø'),
  ('9001','Tromsø'),
  ('9000','Tromsø');

INSERT INTO address (address_id, street, gatenr, city_postnr) VALUES
  (1,'Fjelltoppen','4','8501'),
  (2,'Fjelltoppen','3','8500'),
  (3,'Øvregata','332','8001'),
  (4,'Lillegata','233','8000'),
  (5,'Nedreveien','223','8000'),
  (6,'Veien','124','8000'),
  (7,'Murergata','1','9001'),
  (8,'Murergata','2','9000');

INSERT INTO customer (customer_id, name, type, email, invoice_address_id, delivery_address_id) VALUES
  (20011,'Anders Andersen','Privat','aa@post.no',1,2),
  (10002,'Grøft og Kant AS','Bedrift','gm@uuiitt.nu',3,4),
  (11122,'Lokalbyggern AS','Bedrift','lok_bygg@no.no',5,6),
  (8988,'Murer Pedersen ANS','Bedrift','mu_pe@ånnlain.no',7,8);

INSERT INTO customer_phone VALUES
  ('76900112',20011), ('99988777',20011), ('22122333',20011),
  ('76900111',10002), ('99988877',10002),
  ('70766554',11122),
  ('90099888',8988);

INSERT INTO employee VALUES
  (1,'Hilde Pettersen','10090999'),
  (2,'Berit Hansen','10191999'),
  (3,'Hans Hansen','10291999'),
  (4,'Admin Admin','99999999');
  
INSERT INTO employee_login (employee_id, username, password_hash, role, is_active) VALUES
(4, 'admin', 'admin12345', 'admin', TRUE),
(3, 'hans', 'hans12345', 'user', TRUE);

INSERT INTO equipment_category VALUES
  (1,'Lette maskiner'), (2,'Tunge maskiner'), (3,'Annleggsutstyr');

INSERT INTO equipment_model (model_id, type, brand, model, description, daily_price, total_quantity, equipment_category_id) VALUES
  (233,'Kompressor','Stanley','Vento 6L','Liten og hendig, motor 1.5HK.',79.00,10,1),
  (1001,'Minigraver','Hitachi','ZX10U-6','Minigraver for trange plasser.',1200.00,1,2),
  (7653,'Stilas','Haki Stilas','150','Stilas ca 150 kvm.',350.00,2,3),
  (7654,'Sementblander','Atika','130l 600w','Blander 130L 600W.',230.00,8,3),
  (234,'Spikerpistol','ESSVE','Coil CN-15-65','ESSVE coilpistol.',100.00,50,1);


INSERT INTO equipment_instance VALUES
  (233,1,'2018-03-04','2021-03-04'),
  (1001,1,'2019-09-01','2022-09-01'),
  (7653,1,'2016-11-12','2021-11-12'),
  (7654,1,'2019-03-20','2024-03-20'),
  (233,2,'2017-01-02','2022-01-02'),
  (234,1,'2021-02-10','2022-02-10');
  
INSERT INTO rental
  (rental_id, customer_id, model_id, instans_nr, rent_date, return_date, payment_method,
   employee_id, deliver_to_customer, delivery_cost)
VALUES
  (1,20011,233,1,'2021-02-01',NULL,'Kort',1,TRUE,150.00),
  (2,10002,1001,1,'2021-02-05','2021-02-08','Kontant',1,TRUE,500.00),
  (3,11122,7653,1,'2021-02-05',NULL,'Kort',2,FALSE,0.00),
  (4,8988,7654,1,'2020-02-04','2020-02-10','Vipps',2,TRUE,200.00),
  (5,20011,233,2,'2019-03-05','2019-03-06','Kontant',2,FALSE,0.00),
  (6,11122,234,1,'2019-02-01','2019-02-03','Kort',3,FALSE,0.00);
