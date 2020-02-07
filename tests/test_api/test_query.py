from tests.common import ApiTest, Author, Book


class TestQuery(ApiTest):

    def test_query_one(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save
        
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
        ).save()
        
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

    def test_filter_subset_query(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()
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
                    'count': 1,
                    'total': 1,
                    'edges': [{
                        'node': {
                            'id': author.id,
                            'name': author.name,
                            'book_set': {
                                'count': 1,
                                'total': 1,
                                'edges': [{
                                    'node': {
                                        'id': book1.id,
                                        'name': book1.name
                                    }
                                }]
                            }
                        }
                    }]
                }
            }
        )
