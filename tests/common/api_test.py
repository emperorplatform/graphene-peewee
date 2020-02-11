import json

from graphql.execution import ExecutionResult

from .models import db, Book, Author
from .base_test import BaseTest
from .schema import generate_schema


class ApiTest(BaseTest):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.db = db
        cls.schema, cls.executor = generate_schema(cls.db, [Book, Author])

    def setUp(self):
        Book.delete().execute()
        Author.delete().execute()

    def query(self, query, variables={}):
        pre_result = self.schema.execute(
            query,
            variable_values=variables,
            return_promise=False,
            executor=self.executor
        )        
        if isinstance(pre_result, ExecutionResult):
            result = pre_result
        else:
            result = pre_result
        # TODO: better way to convert OrderedDict to simple dict
        dumped_data = json.dumps(result.data)
        result.data = json.loads(dumped_data)
        return result