-- 03_create_views.sql

CREATE VIEW authors_books AS
SELECT 
   a.first_name,
   a.last_name,
   b.title
FROM authors a
JOIN authors_books ab ON a.author_id = ab.author_id
JOIN books b on b.book_id = ab.book_id;
