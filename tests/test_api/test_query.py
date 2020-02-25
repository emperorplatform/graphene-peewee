from tests.common import ApiTest, Author, Book, Page, db


class TestQuery(ApiTest):

    def test_query_one(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
        
        book = Book(
            name='bar', 
            year=2000, 
            author=author
        )
        book.save()

        result = self.query('''
            query {
                book (id: ''' + str(book.id) + ''') {
                    id
                    name
                    year
                    author {
                        id
                        name
                        rating
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'book': {
                    'id': book.id,
                    'name': book.name,
                    'year': book.year,
                    'author': {
                        'id': author.id,
                        'name': author.name,
                        'rating': author.rating
                    }
                }
            }
        )

    def test_query_empty(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
        book = Book(
            name='bar', 
            year=2000, 
            author=author
        )
        book.save()

        result = self.query('''
            query {
                book {
                    id
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'book': {
                    'id': book.id,
                }
            }
        )

    def test_query_many(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
        
        book1 = Book(
            name='bar1', 
            year=2002, 
            author=author
        )
        book1.save()
        
        book2 = Book(
            name='bar2', 
            year=2001, 
            author=author
        )
        book2.save()
        
        book3 = Book(
            name='bar3', 
            year=2003, 
            author=author
        )
        book3.save()

        result = self.query('''
            query {
                books (
                    filters: {
                        author__rating: ''' + str(author.rating) + '''
                    },
                    order_by: ["-author__name", "year"],
                    page: 1,
                    paginate_by: 2
                ) {
                    total
                    count
                    edges {
                        node {
                            id
                            name
                            year
                            author {
                                id
                                name
                                rating
                            }
                        }
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'books': {
                    'count': 2,
                    'total': 3,
                    'edges': [{
                        'node': {
                            'id': book2.id,
                            'name': book2.name,
                            'year': book2.year,
                            'author': {
                                'id': author.id,
                                'name': author.name,
                                'rating': author.rating
                            }
                        }
                    }, {
                        'node': {
                            'id': book1.id,
                            'name': book1.name,
                            'year': book1.year,
                            'author': {
                                'id': author.id,
                                'name': author.name,
                                'rating': author.rating
                            }
                        }
                    }]
                }
            }
        )
    
    def test_query_many_filter_on_foreign_key(self):
        self.maxDiff = None
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
        
        book1 = Book(
            name='bar1', 
            year=2002, 
            author=author
        )
        book1.save()
        
        book2 = Book(
            name='bar2', 
            year=2001, 
            author=author
        )
        book2.save()
        
        book3 = Book(
            name='bar3', 
            year=2003, 
            author=author
        )
        book3.save()

        result = self.query('''
            query {
                books (
                    filters: {
                        author_id: 1
                    },
                ) {
                    edges {
                        node {
                            id
                            name
                            year
                        }
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'books': {
                    'edges': [{
                        'node': {
                            'id': book1.id,
                            'name': book1.name,
                            'year': book1.year
                        }
                    }, {
                        'node': {
                            'id': book2.id,
                            'name': book2.name,
                            'year': book2.year
                        }
                    }, {
                        'node': {
                        'id': book3.id,
                        'name': book3.name,
                        'year': book3.year
                        }
                    }]
                }
            }
        )
    
    def test_query_many_nested_foreign_key_relation(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
        
        book = Book(
            name='bar', 
            year=2000, 
            author=author
        )
        book.save()

        page = Page(
            chapter=4,
            number=3,
            book=book
        )
        page.save()

        result = self.query('''
            query {
                pages {
                    edges {
                        node {
                            book {
                                author {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'pages': {
                    'edges': [
                        {
                            'node': {
                                'book': {
                                    'author': {
                                        'name': 'foo'
                                    }
                                }
                            }

                        }
                    ]
                }
            }
        )

    def test_filter_subset_query(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
        author2 = Author(
            name='bar', 
            rating=42
        )
        author2.save()
        book1 = Book(
            name='bar1', 
            year=2001, 
            author=author
        )
        book1.save()
        book2 = Book(
            name='bar2', 
            year=2002, 
            author=author
        )
        book2.save()
        book3 = Book(
            name='bar1', 
            year=2002, 
            author=author2
        )
        book3.save()

        result = self.query('''
            query {
                authors {
                    count
                    total
                    edges {
                        node {
                            id
                            name
                            book_set (filters: {name: "bar1"}) {
                                count
                                total
                                edges {
                                    node {
                                        id
                                        name
                                    }
                                }
                            }
                        }
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'authors': {
                    'count': 2,
                    'total': 2,
                    'edges': [
                        {
                            'node': {
                                'id': author.id,
                                'name': author.name,
                                'book_set': {
                                    'count': 1,
                                    'total': 2,
                                    'edges': [{
                                        'node': {
                                            'id': book1.id,
                                            'name': book1.name
                                        }
                                    }]
                                }
                            }
                        },
                        {
                            'node': {
                                'id': author2.id,
                                'name': author2.name,
                                'book_set': {
                                    'count': 1,
                                    'total': 1,
                                    'edges': [{
                                        'node': {
                                            'id': book3.id,
                                            'name': book3.name
                                        }
                                    }]
                                }
                            }
                        }
                    ]
                }
            }
        )
