def test_graphql_resolver():
    from src.api.graphql import GraphQLResolver
    assert GraphQLResolver().resolve_profile()['bio'] == 'resolved'
