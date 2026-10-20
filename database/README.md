## Structure

| Directory | Responsibility         | Main SQL statements                        |
| --------- | ---------------------- | ------------------------------------------ |
| `ddl/`    | Database structure     | `CREATE`, `ALTER`, `DROP`, `TRUNCATE`      |
| `dml/`    | Data modification      | `INSERT`, `UPDATE`, `DELETE`, `MERGE`      |
| `dql/`    | Data retrieval         | `SELECT`                                   |
| `dcl/`    | Access control         | `GRANT`, `REVOKE`                          |
| `tcl/`    | Transaction management | `BEGIN`, `COMMIT`, `ROLLBACK`, `SAVEPOINT` |


## 1. DDL — Data Definition Language

Purpose: Defines and modifies database structures, such as tables, schemas, indexes, and constraints.

`ddl/01_create_tables.sql`

```
CREATE TABLE authors (
    author_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name VARCHAR(100) NOT NULL
);

CREATE TABLE books (
    book_id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    author_id INTEGER REFERENCES authors(author_id),
    price DECIMAL(10, 2) CHECK (price >= 0)
);

CREATE INDEX idx_books_author
ON books(author_id);
```

Other DDL statements:

```
ALTER TABLE books ADD COLUMN published_at DATE;

DROP INDEX idx_books_author;

TRUNCATE TABLE books;

DROP TABLE books;
```

## 2. DML — Data Manipulation Language

Purpose: Inserts, updates, and deletes records stored in tables.

`dml/01_manage_books.sql`

```
-- INSERT
INSERT INTO authors (name)
VALUES ('George Orwell');

INSERT INTO books (title, author_id, price)
VALUES ('1984', 1, 299.00);

-- UPDATE
UPDATE books
SET price = 349.00
WHERE book_id = 1;

-- DELETE
DELETE FROM books
WHERE book_id = 1;
```

## 3. DQL — Data Query Language

Purpose: Retrieves and analyzes data without modifying stored records.

`dql/01_books_analysis.sql`

```
SELECT
    a.name AS author,
    COUNT(b.book_id) AS book_count,
    AVG(b.price) AS average_price
FROM authors AS a
JOIN books AS b
    ON a.author_id = b.author_id
WHERE b.price > 100
GROUP BY a.author_id, a.name
HAVING COUNT(b.book_id) >= 1
ORDER BY average_price DESC
LIMIT 10;
```

This example demonstrates `SELECT`, `JOIN`, `WHERE`, `GROUP BY`, `HAVING`, `ORDER BY`, and `LIMIT`.

## 4. DCL — Data Control Language

Purpose: Manages database permissions and access privileges.

`dcl/01_permissions.sql`

```
-- Create a database role (PostgreSQL)
CREATE ROLE librarian LOGIN PASSWORD 'example_password';

-- Grant read access
GRANT SELECT ON books TO librarian;

-- Grant modification permissions
GRANT INSERT, UPDATE ON books TO librarian;

-- Revoke modification permissions
REVOKE INSERT, UPDATE ON books FROM librarian;
```

`CREATE ROLE` is generally classified as DDL, while `GRANT` and `REVOKE` are DCL.

## 5. TCL — Transaction Control Language

Purpose: Controls transactions to ensure that related database operations are committed or rolled back together.

`tcl/01_book_transaction.sql`

```
-- Begin transaction
BEGIN;

UPDATE books
SET price = price * 1.10
WHERE author_id = 1;

-- Create savepoint
SAVEPOINT before_discount;

UPDATE books
SET price = price * 0.50
WHERE author_id = 1;

-- Undo discount, preserve first update
ROLLBACK TO SAVEPOINT before_discount;

-- Persist changes
COMMIT;
```

If you wanted to undo the entire transaction instead, you would use `ROLLBACK;` before committing.
