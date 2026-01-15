from flask import Blueprint, request, jsonify
from flask_restx import Api, Resource, fields
from services.sparql_service import SparqlService
from services.dbpedia_service import DbpediaService
import os

api_blueprint = Blueprint('api', __name__, url_prefix='/api')
api = Api(api_blueprint, title="Cycling Tour Operator API", version="1.0", description="API for querying RDF data",  doc='/docs')

database_folder = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database')
ttl_files = [
    os.path.join(database_folder, file)
    for file in os.listdir(database_folder)
    if file.endswith('.ttl')
]

sparql_service = SparqlService(ttl_files)
dbpedia_service = DbpediaService()

query_model = api.model('Query', {
    'query': fields.String(required=True, description='SPARQL query to execute')
})

enrich_model = api.model('EnrichQuery', {
    'query': fields.String(required=True, description='SPARQL query to fetch local data')
})

@api.route('/query')
class QueryEndpoint(Resource):
    @api.expect(query_model)
    def post(self):
        """Execute a SPARQL query on the local RDF graph"""
        query = request.json.get('query')
        if not query:
            return {'error': 'Query is required'}, 400
        
        try:
            results = sparql_service.execute_query(query)
            return results, 200
        except Exception as e:
            return {'error': str(e)}, 500

@api.route('/enrich')
class EnrichEndpoint(Resource):
    @api.expect(enrich_model)
    def post(self):
        """Enrich local data with remote DBpedia data"""
        local_query = request.json.get('query')
        if not local_query:
            return {'error': 'Query is required'}, 400
        
        try:
            local_results = sparql_service.execute_query(local_query)
            
            uris_to_fetch = set()
            for row in local_results:
                uri = row.get('sameAs')
                if uri:
                    uris_to_fetch.add(uri)
            
            remote_data = dbpedia_service.get_enriched_data_bulk(list(uris_to_fetch))
            
            final_response = []
            for row in local_results:
                merged_item = row.copy()
                
                uri_key = row.get('sameAs')
                
                if uri_key and uri_key in remote_data:
                    merged_item.update(remote_data[uri_key])
                
                final_response.append(merged_item)
                
            return final_response, 200

        except Exception as e:
            return {'error': str(e)}, 500

