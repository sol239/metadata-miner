-- 02_seed_large_data.sql
-- Oracle Database 23c / Oracle Free
-- Run against an empty library schema after 01_create_tables.sql.
-- All records are synthetic. Run once; this script is not idempotent.

SET SERVEROUTPUT ON;

/**
Publishers (100)
Publisher names are synthetic and unique for this dataset.
*/
INSERT INTO publishers (name)
SELECT 'Publisher ' || LPAD(LEVEL, 3, '0')
FROM dual CONNECT BY LEVEL <= 100;

/**
Authors (2,000)
Repeated first and last names intentionally simulate ambiguous names.
*/
INSERT INTO authors (first_name, last_name)
SELECT
    CASE MOD(LEVEL, 12)
        WHEN 0 THEN 'Anna' WHEN 1 THEN 'James' WHEN 2 THEN 'Maria'
        WHEN 3 THEN 'David' WHEN 4 THEN 'Eva' WHEN 5 THEN 'Oliver'
        WHEN 6 THEN 'Sofia' WHEN 7 THEN 'Thomas' WHEN 8 THEN 'Emma'
        WHEN 9 THEN 'Daniel' WHEN 10 THEN 'Laura' ELSE 'Michael'
    END,
    CASE MOD(TRUNC((LEVEL - 1) / 12), 12)
        WHEN 0 THEN 'Novak' WHEN 1 THEN 'Smith' WHEN 2 THEN 'Brown'
        WHEN 3 THEN 'Miller' WHEN 4 THEN 'Wilson' WHEN 5 THEN 'Dvorak'
        WHEN 6 THEN 'Taylor' WHEN 7 THEN 'Martin' WHEN 8 THEN 'Clark'
        WHEN 9 THEN 'Anderson' WHEN 10 THEN 'Walker' ELSE 'Johnson'
    END
FROM dual CONNECT BY LEVEL <= 2000;

/**
Members (10,000)
Registration dates span approximately eight years.
Emails are unique, while member names intentionally repeat.
*/
INSERT INTO members (first_name, last_name, email, registration_date)
SELECT
    CASE MOD(LEVEL, 10)
        WHEN 0 THEN 'Alice' WHEN 1 THEN 'Bob' WHEN 2 THEN 'Caroline'
        WHEN 3 THEN 'David' WHEN 4 THEN 'Emma' WHEN 5 THEN 'Frank'
        WHEN 6 THEN 'Grace' WHEN 7 THEN 'Henry' WHEN 8 THEN 'Iris'
        ELSE 'Jack'
    END,
    CASE MOD(TRUNC((LEVEL - 1) / 10), 10)
        WHEN 0 THEN 'Novak' WHEN 1 THEN 'Smith' WHEN 2 THEN 'Dvorak'
        WHEN 3 THEN 'Brown' WHEN 4 THEN 'Wilson' WHEN 5 THEN 'Miller'
        WHEN 6 THEN 'Taylor' WHEN 7 THEN 'Clark' WHEN 8 THEN 'Martin'
        ELSE 'Walker'
    END,
    'member' || LPAD(LEVEL, 6, '0') || '@example.test',
    DATE '2018-01-01' + MOD(LEVEL * 37, 3200)
FROM dual CONNECT BY LEVEL <= 10000;

/**
Books (20,000)
Publisher distribution is skewed: approximately half of books belong
 to the first ten publishers. Some publication years and ISBNs are unknown.
*/
INSERT INTO books (title, publication_year, isbn, publisher_id)
SELECT
    CASE MOD(LEVEL, 8)
        WHEN 0 THEN 'Introduction to' WHEN 1 THEN 'Advanced'
        WHEN 2 THEN 'Practical' WHEN 3 THEN 'History of'
        WHEN 4 THEN 'The Art of' WHEN 5 THEN 'Foundations of'
        WHEN 6 THEN 'Modern' ELSE 'Handbook of'
    END || ' ' ||
    CASE MOD(TRUNC((LEVEL - 1) / 8), 10)
        WHEN 0 THEN 'Data' WHEN 1 THEN 'Literature'
        WHEN 2 THEN 'Science' WHEN 3 THEN 'Computing'
        WHEN 4 THEN 'Economics' WHEN 5 THEN 'Mathematics'
        WHEN 6 THEN 'History' WHEN 7 THEN 'Philosophy'
        WHEN 8 THEN 'Engineering' ELSE 'Design'
    END || ' Volume ' || TO_CHAR(LEVEL),
    CASE WHEN MOD(LEVEL, 17) = 0 THEN NULL
         ELSE 1950 + MOD(LEVEL * 13, 77) END,
    CASE WHEN MOD(LEVEL, 19) = 0 THEN NULL
         ELSE '978' || LPAD(TO_CHAR(LEVEL), 10, '0') END,
    CASE WHEN MOD(LEVEL, 2) = 0 THEN 1 + MOD(LEVEL * 7, 10)
         ELSE 11 + MOD(LEVEL * 17, 90) END
FROM dual CONNECT BY LEVEL <= 20000;

/**
Physical copies (50,000)
Books 1-10,000 have three copies each; books 10,001-20,000 have two.
Availability status deliberately has no documented business meaning.
*/
INSERT INTO physical_copies (barcode, book_id, availability_status)
SELECT
    'COPY-' || LPAD(LEVEL, 8, '0'),
    CASE WHEN LEVEL <= 30000 THEN CEIL(LEVEL / 3)
         ELSE 10000 + CEIL((LEVEL - 30000) / 2) END,
    CASE WHEN MOD(LEVEL, 29) = 0 THEN 2
         WHEN MOD(LEVEL, 11) = 0 THEN 0
         ELSE 1 END
FROM dual CONNECT BY LEVEL <= 50000;

/**
Authors-Books (30,000)
Every book has one author; even-numbered books have a second author.
Composite primary keys are never duplicated.
*/
INSERT INTO authors_books (author_id, book_id)
SELECT 1 + MOD(book_id * 17, 2000), book_id
FROM (SELECT LEVEL AS book_id FROM dual CONNECT BY LEVEL <= 20000);

INSERT INTO authors_books (author_id, book_id)
SELECT 1 + MOD(book_id * 17 + 1, 2000), book_id
FROM (SELECT LEVEL * 2 AS book_id FROM dual CONNECT BY LEVEL <= 10000);

/**
Loans (150,000)
Three historical loans are generated for each physical copy.
A subset of copies also receives a fourth, currently active loan.
Historical loan periods do not overlap for a given copy.
*/
INSERT INTO loans (
    member_id, physical_copy_id, borrowing_date, due_date, actual_return_date
)
SELECT
    1 + MOD(copy_id * 13 + loan_round * 101, 10000),
    copy_id,
    DATE '2020-01-01' + MOD(copy_id * 7, 1500) + (loan_round - 1) * 90,
    DATE '2020-01-01' + MOD(copy_id * 7, 1500) + (loan_round - 1) * 90 + 21,
    DATE '2020-01-01' + MOD(copy_id * 7, 1500) + (loan_round - 1) * 90
        + CASE WHEN MOD(copy_id + loan_round, 7) = 0 THEN 28 ELSE 14 END
FROM (
    SELECT LEVEL AS copy_id FROM dual CONNECT BY LEVEL <= 50000
) c
CROSS JOIN (
    SELECT LEVEL AS loan_round FROM dual CONNECT BY LEVEL <= 3
) r;

-- Add 10,000 active loans, bringing the total to 160,000 loans.
-- Active loan dates are recent and occur after each copy's historical loans.
INSERT INTO loans (
    member_id, physical_copy_id, borrowing_date, due_date, actual_return_date
)
SELECT
    1 + MOD(copy_id * 19, 10000),
    copy_id,
    DATE '2026-10-01' + MOD(copy_id, 15),
    DATE '2026-10-01' + MOD(copy_id, 15) + 21,
    NULL
FROM (
    SELECT LEVEL * 5 AS copy_id FROM dual CONNECT BY LEVEL <= 10000
);

COMMIT;

-- Refresh optimizer statistics for metadata exploration and query planning.
BEGIN
    DBMS_STATS.GATHER_SCHEMA_STATS(ownname => USER, cascade => TRUE);
END;
/

-- Verify row counts.
SELECT 'MEMBERS' AS table_name, COUNT(*) AS row_count FROM members
UNION ALL SELECT 'AUTHORS', COUNT(*) FROM authors
UNION ALL SELECT 'PUBLISHERS', COUNT(*) FROM publishers
UNION ALL SELECT 'BOOKS', COUNT(*) FROM books
UNION ALL SELECT 'PHYSICAL_COPIES', COUNT(*) FROM physical_copies
UNION ALL SELECT 'AUTHORS_BOOKS', COUNT(*) FROM authors_books
UNION ALL SELECT 'LOANS', COUNT(*) FROM loans;

-- Confirm no physical copy has multiple active loans.
SELECT physical_copy_id, COUNT(*) AS active_loan_count
FROM loans
WHERE actual_return_date IS NULL
GROUP BY physical_copy_id
HAVING COUNT(*) > 1;
