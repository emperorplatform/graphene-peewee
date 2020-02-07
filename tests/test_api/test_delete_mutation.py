import json

from tests.common import ApiTest, Author


class TestDeleteMutation(ApiTest):

    def test_delete_one(self):
        author = Author(
            name='foo', 
            rating=42
        )
        author.save()

        result = self.query('''
            mutation {
                delete_author (id: ''' + str(author.id) + ''') {
                    affected {
                        id
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'delete_author': {
                    'affected': {
                        'id': author.id
                    }
                }
            }
        )

    def test_delete_many(self):
        author1 = Author(
            name='foo', 
            rating=42
        )
        author1.save()
    
        author2 = Author(
            name='bar', 
            rating=9000
        )
        author2.save()

        result = self.query('''
            mutation {
                delete_authors (
                    filters: {
                        id__in: ''' + json.dumps([author1.id, author2.id]) + '''
                    }
                ) {
                    affected {
                        total
                    }
                }
            }
        ''')

        self.assertIsNone(result.errors)
        self.assertEqual(
            result.data,
            {
                'delete_authors': {
                    'affected': {
                        'total': 2
                    }
                }
            }
        )
