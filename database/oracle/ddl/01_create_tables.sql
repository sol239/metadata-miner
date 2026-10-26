
-- 01_create_tables.sql

-- ============================================================
-- ENTITY TABLES
-- ============================================================

-- Members
CREATE TABLE members (
    member_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    first_name VARCHAR2(100) NOT NULL,
    last_name VARCHAR2(100) NOT NULL,
    email VARCHAR2(100) NOT NULL,
    registration_date DATE NOT NULL,
    CONSTRAINT pk_members PRIMARY KEY (member_id),
    CONSTRAINT uq_members_email UNIQUE (email)
);

COMMENT ON TABLE members IS
    'Registered library members who can borrow physical book copies.';

COMMENT ON COLUMN members.member_id IS
    'Unique system-generated identifier of a library member.';

COMMENT ON COLUMN members.first_name IS
    'First name of the library member.';

COMMENT ON COLUMN members.last_name IS
    'Last name of the library member.';

COMMENT ON COLUMN members.email IS
    'Unique email address of the library member.';

COMMENT ON COLUMN members.registration_date IS
    'Date when the member registered with the library.';


-- Authors
CREATE TABLE authors (
    author_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    first_name VARCHAR2(100) NOT NULL,
    last_name VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_authors PRIMARY KEY (author_id)
);

COMMENT ON TABLE authors IS
    'Authors associated with books in the library catalog.';

COMMENT ON COLUMN authors.author_id IS
    'Unique system-generated identifier of an author.';

COMMENT ON COLUMN authors.first_name IS
    'First name of the author.';

COMMENT ON COLUMN authors.last_name IS
    'Last name of the author.';


-- Publishers
CREATE TABLE publishers (
    publisher_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    name VARCHAR2(100) NOT NULL,
    CONSTRAINT pk_publishers PRIMARY KEY (publisher_id)
);

COMMENT ON TABLE publishers IS
    'Publishing organizations responsible for publishing books.';

COMMENT ON COLUMN publishers.publisher_id IS
    'Unique system-generated identifier of a publisher.';

COMMENT ON COLUMN publishers.name IS
    'Name of the publishing organization.';


-- Books
CREATE TABLE books (
    book_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    title VARCHAR2(100) NOT NULL,
    publication_year NUMBER(4),
    isbn VARCHAR2(17),
    publisher_id NUMBER(10) NOT NULL,
    CONSTRAINT pk_books PRIMARY KEY (book_id),
    CONSTRAINT uq_books_isbn UNIQUE (isbn),
    CONSTRAINT fk_books_publisher
        FOREIGN KEY (publisher_id)
        REFERENCES publishers (publisher_id)
);

COMMENT ON TABLE books IS
    'Bibliographic records representing book titles and editions. Each book belongs to one publisher and may have multiple authors and physical copies.';

COMMENT ON COLUMN books.book_id IS
    'Unique system-generated identifier of a bibliographic book record.';

COMMENT ON COLUMN books.title IS
    'Title of the book.';

COMMENT ON COLUMN books.publication_year IS
    'Calendar year in which the book was published.';

COMMENT ON COLUMN books.isbn IS
    'Unique International Standard Book Number (ISBN) identifying the book edition.';

COMMENT ON COLUMN books.publisher_id IS
    'Foreign key referencing the publisher responsible for the book.';


-- Physical Copies
CREATE TABLE physical_copies (
    physical_copy_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    barcode VARCHAR2(100) NOT NULL,
    book_id NUMBER(10) NOT NULL,
    availability_status NUMBER(1) DEFAULT 1 NOT NULL,
    CONSTRAINT pk_physical_copies PRIMARY KEY (physical_copy_id),
    CONSTRAINT uq_physical_copies_barcode UNIQUE (barcode),
    CONSTRAINT fk_copies_book
        FOREIGN KEY (book_id)
        REFERENCES books (book_id)
);

COMMENT ON TABLE physical_copies IS
    'Individual physical copies of books owned by the library. A book may have multiple physical copies, each identified by a unique barcode.';

COMMENT ON COLUMN physical_copies.physical_copy_id IS
    'Unique system-generated identifier of a physical book copy.';

COMMENT ON COLUMN physical_copies.barcode IS
    'Unique barcode used to identify and track the physical copy.';

COMMENT ON COLUMN physical_copies.book_id IS
    'Foreign key referencing the bibliographic book record.';

COMMENT ON COLUMN physical_copies.availability_status IS
    'Availability indicator of the physical copy. Default value 1; application-defined status values.';


-- ============================================================
-- RELATIONSHIP TABLES
-- ============================================================

/**
 * Authors-Books relationship table (M:N).
 *
 * Each author can be associated with multiple books.
 * Each book can be associated with multiple authors.
 *
 * The composite primary key prevents duplicate associations.
 */
CREATE TABLE authors_books (
    author_id NUMBER(10) NOT NULL,
    book_id NUMBER(10) NOT NULL,
    CONSTRAINT pk_authors_books PRIMARY KEY (author_id, book_id),
    CONSTRAINT fk_ab_author
        FOREIGN KEY (author_id)
        REFERENCES authors (author_id),
    CONSTRAINT fk_ab_book
        FOREIGN KEY (book_id)
        REFERENCES books (book_id)
);

COMMENT ON TABLE authors_books IS
    'Associative table implementing the many-to-many relationship between authors and books. Each row represents one author-book association.';

COMMENT ON COLUMN authors_books.author_id IS
    'Foreign key referencing an author associated with the book.';

COMMENT ON COLUMN authors_books.book_id IS
    'Foreign key referencing a book associated with the author.';


/**
 * Loans table.
 *
 * Relationships:
 * Members (1:N) Loans
 * Physical Copies (1:N) Loans
 *
 * Each member can have multiple loans over time.
 * Each physical copy can be borrowed multiple times.
 *
 * Business rules:
 * - Only one active loan is allowed per physical copy.
 * - A loan is active when actual_return_date IS NULL.
 * - The due date cannot precede the borrowing date.
 * - The return date cannot precede the borrowing date.
 *
 * The virtual column active_copy_id and its UNIQUE
 * constraint enforce the active-loan rule.
 */
CREATE TABLE loans (
    loan_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    member_id NUMBER(10) NOT NULL,
    physical_copy_id NUMBER(10) NOT NULL,
    borrowing_date DATE NOT NULL,
    due_date DATE NOT NULL,
    actual_return_date DATE,
    active_copy_id NUMBER(10) GENERATED ALWAYS AS (
        CASE
            WHEN actual_return_date IS NULL
                THEN physical_copy_id
        END
    ) VIRTUAL,
    CONSTRAINT pk_loans PRIMARY KEY (loan_id),
    CONSTRAINT fk_loans_member
        FOREIGN KEY (member_id)
        REFERENCES members (member_id),
    CONSTRAINT fk_loans_copy
        FOREIGN KEY (physical_copy_id)
        REFERENCES physical_copies (physical_copy_id),
    CONSTRAINT uq_active_loan UNIQUE (active_copy_id),
    CONSTRAINT chk_loans_due_date
        CHECK (due_date >= borrowing_date),
    CONSTRAINT chk_loans_return_date
        CHECK (
            actual_return_date IS NULL
            OR actual_return_date >= borrowing_date
        )
);

COMMENT ON TABLE loans IS
    'Historical and active borrowing transactions linking library members to physical book copies. Only one active loan per physical copy is permitted.';

COMMENT ON COLUMN loans.loan_id IS
    'Unique system-generated identifier of a borrowing transaction.';

COMMENT ON COLUMN loans.member_id IS
    'Foreign key referencing the member who borrowed the physical copy.';

COMMENT ON COLUMN loans.physical_copy_id IS
    'Foreign key referencing the physical book copy being borrowed.';

COMMENT ON COLUMN loans.borrowing_date IS
    'Date when the physical copy was borrowed by the member.';

COMMENT ON COLUMN loans.due_date IS
    'Scheduled return deadline. Must be greater than or equal to the borrowing date.';

COMMENT ON COLUMN loans.actual_return_date IS
    'Actual date when the borrowed copy was returned. NULL indicates an active loan.';

COMMENT ON COLUMN loans.active_copy_id IS
    'Virtual column containing physical_copy_id for active loans and NULL for returned loans. A unique constraint prevents concurrent active loans for the same copy.';
