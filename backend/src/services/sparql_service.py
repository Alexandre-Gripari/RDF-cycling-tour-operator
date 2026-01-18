from rdflib import Graph, URIRef, Namespace
from rdflib.namespace import RDFS
import owlrl

CS = Namespace("http://data.cyclingtour.fr/schema#")
CTO = Namespace("http://data.cyclingtour.fr/data#")

class SparqlService:
    def __init__(self, ttl_files):
        self.graph = Graph()
        self.graph.bind("cs", CS)
        self.graph.bind("cto", CTO)
        self.graph.bind("rdfs", RDFS)
        
        self._load_ttl_files(ttl_files)
        self.apply_inference()

    def _load_ttl_files(self, ttl_files):
        for ttl_file in ttl_files:
            try:
                self.graph.parse(ttl_file, format="turtle")
                print(f"Loaded {ttl_file} successfully.")
            except Exception as e:
                print(f"Error loading {ttl_file}: {e}")

    def apply_inference(self):
        print("Applying RDFS inference...")
        owlrl.DeductiveClosure(owlrl.RDFS_Semantics).expand(self.graph)

    def execute_query(self, query):
        try:
            results = self.graph.query(query)
            return [{str(var): str(row[var]) for var in row.labels} for row in results]
        except Exception as e:
            raise Exception(f"Error executing query: {e}")

    def get_graph(self):
        return self.graph
    
    def predict_recommendations(self, client_uri):
        client_ref = URIRef(client_uri) 
        
        query_target = """
        SELECT ?tour WHERE {
            ?booking a cs:TourBooking ;
                     cs:bookedBy ?client ;
                     cs:tourPackageBooked ?tour .
        }"""
        
        results_target = self.graph.query(query_target, initBindings={'client': client_ref})
        target_tours = {row.tour for row in results_target}
        
        if not target_tours:
            return []

        query_others = """
        SELECT DISTINCT ?other WHERE {
            ?booking a cs:TourBooking ;
                     cs:bookedBy ?other .
            FILTER (?other != ?target)
        }"""
        
        results_others = self.graph.query(query_others, initBindings={'target': client_ref})
        other_clients = [row.other for row in results_others]
        
        candidates = {} 

        query_history = """
        SELECT ?tour WHERE {
            ?booking a cs:TourBooking ;
                     cs:bookedBy ?client ;
                     cs:tourPackageBooked ?tour .
        }"""

        for other_client_ref in other_clients:
            results_other = self.graph.query(query_history, initBindings={'client': other_client_ref})
            other_tours = {row.tour for row in results_other}
            
            intersection = target_tours.intersection(other_tours)
            union = target_tours.union(other_tours)
            
            if len(union) == 0: continue
            
            jaccard_score = len(intersection) / len(union)
            
            if jaccard_score > 0:
                potential_new_links = other_tours - target_tours
                for tour in potential_new_links:
                    if tour not in candidates:
                        candidates[tour] = 0.0
                    candidates[tour] += jaccard_score

        recommendations = []
        for tour_uri, score in candidates.items():
            label_res = self.graph.query(
                "SELECT ?label WHERE { ?tour rdfs:label ?label }", 
                initBindings={'tour': tour_uri}
            )
            label = next(iter(label_res)).label if label_res else str(tour_uri)

            recommendations.append({
                "tour_uri": str(tour_uri),
                "label": str(label),
                "score": round(score, 3),
            })

        recommendations.sort(key=lambda x: x['score'], reverse=True)
        return recommendations
