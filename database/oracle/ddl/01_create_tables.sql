CREATE TABLE books (
    book_id NUMBER(10) GENERATED ALWAYS AS IDENTITY,
    title VARCHAR2(100) NOT NULL,
    published_date DATE,
    isbn VARCHAR2(17),
    author_id NUMBER(10)

    CONSTRAINT pk_books PRIMARY KEY (book_id),
    CONSTRAINT pk_books_isbn UNIQUE (isbn),
);