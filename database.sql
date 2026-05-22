CREATE DATABASE IF NOT EXISTS biblioteca_open CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE biblioteca_open;

DROP TABLE IF EXISTS prestamos;
DROP TABLE IF EXISTS libros;
DROP TABLE IF EXISTS usuarios;

CREATE TABLE usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario VARCHAR(100) NOT NULL,
    correo VARCHAR(150) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE libros (
    id INT AUTO_INCREMENT PRIMARY KEY,
    titulo VARCHAR(150) NOT NULL,
    autor VARCHAR(150) NOT NULL,
    categoria VARCHAR(100) NOT NULL,
    total INT NOT NULL,
    prestados INT DEFAULT 0,
    imagen VARCHAR(255),
    pdf VARCHAR(255),
    precio_prestamo DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE prestamos (
    id INT AUTO_INCREMENT PRIMARY KEY,
    usuario_id INT NOT NULL,
    libro_id INT NOT NULL,
    nombre_persona VARCHAR(150) NOT NULL,
    celular VARCHAR(30),
    direccion VARCHAR(255),
    estado ENUM('solicitado','enviado','prestado','devolucion_solicitada','recogida','devuelto') DEFAULT 'solicitado',
    fecha_solicitud DATETIME DEFAULT CURRENT_TIMESTAMP,
    fecha_envio DATETIME NULL,
    fecha_prestamo DATETIME NULL,
    fecha_devolucion DATETIME NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE CASCADE,
    FOREIGN KEY (libro_id) REFERENCES libros(id) ON DELETE CASCADE
);

INSERT INTO libros (titulo, autor, categoria, total, prestados, imagen, pdf, precio_prestamo) VALUES
('El principito', 'Antoine de Saint-Exupéry', 'Clásico', 10, 0, 'img/principito.jpg', 'principito.pdf', 3000),
('Cien años de soledad', 'Gabriel García Márquez', 'Novela', 6, 0, 'img/cien_anos.jpg', 'cien_anos.pdf', 4000),
('Don Quijote de la Mancha', 'Miguel de Cervantes', 'Clásico', 4, 0, 'img/quijote.jpg', 'quijote.pdf', 3500),
('La Odisea', 'Homero', 'Clásico', 5, 0, 'img/odisea.jpg', 'odisea.pdf', 3000),
('Harry Potter y la piedra filosofal', 'J. K. Rowling', 'Fantasía', 8, 0, 'img/harry.jpg', 'harry.pdf', 4500),
('Orgullo y prejuicio', 'Jane Austen', 'Romance', 5, 0, 'img/orgullo.jpg', 'orgullo.pdf', 3000),
('Crónica de una muerte anunciada', 'Gabriel García Márquez', 'Novela', 6, 0, 'img/cronica.jpg', 'cronica.pdf', 3500),
('El Hobbit', 'J. R. R. Tolkien', 'Fantasía', 7, 0, 'img/hobbit.jpg', 'hobbit.pdf', 4000),
('Drácula', 'Bram Stoker', 'Terror', 5, 0, 'img/dracula.jpg', 'dracula.pdf', 3000),
('Romeo y Julieta', 'William Shakespeare', 'Teatro', 5, 0, 'img/romeo.jpg', 'romeo.pdf', 3000),
('Moby Dick', 'Herman Melville', 'Aventura', 5, 0, 'img/mobydick.jpg', 'mobydick.pdf', 3500),
('El retrato de Dorian Gray', 'Oscar Wilde', 'Novela', 5, 0, 'img/dorian.jpg', 'dorian.pdf', 3500),
('Alicia en el país de las maravillas', 'Lewis Carroll', 'Fantasía', 5, 0, 'img/alicia.jpg', 'alicia.pdf', 3000),
('Frankenstein', 'Mary Shelley', 'Terror', 5, 0, 'img/frankenstein.jpg', 'frankenstein.pdf', 3000);
