from flask import Blueprint, request, jsonify
from services.sparql_service import SparqlService
from services.dbpedia_service import DbpediaService
import os

api = Blueprint('api', __name__)

database_folder = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'database')
ttl_files = [
    os.path.join(database_folder, file)
    for file in os.listdir(database_folder)
    if file.endswith('.ttl')
]

sparql_service = SparqlService(ttl_files)
dbpedia_service = DbpediaService()

@api.route('/query', methods=['POST'])
def execute_query():
    query = request.json.get('query')
    if not query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        results = sparql_service.execute_query(query)
        return jsonify(results), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api.route('/dbpedia/enrich', methods=['POST'])
def get_enriched_mountains():
    local_query = request.json.get('query')
    if not local_query:
        return jsonify({'error': 'Query is required'}), 400
    
    try:
        local_results = sparql_service.execute_query(local_query)
        
        uris_to_fetch = set()
        for row in local_results:
            uri = row.get('dbpediaURI') or row.get('sameAs')
            if uri:
                uris_to_fetch.add(uri)
        
        remote_data = dbpedia_service.get_enriched_data_bulk(list(uris_to_fetch))
        
        final_response = []
        for row in local_results:
            merged_item = row.copy()
            
            uri_key = row.get('dbpediaURI') or row.get('sameAs')
            
            if uri_key and uri_key in remote_data:
                merged_item.update(remote_data[uri_key])
            
            final_response.append(merged_item)
            
        return jsonify(final_response), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
