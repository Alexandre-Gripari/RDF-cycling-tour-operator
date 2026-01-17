import os
import pickle
from sentence_transformers import SentenceTransformer, util
import torch
from google import genai

class ChatBotService:
    def __init__(self, graph, api_key, cache_file="search_index.pkl"):
        self.model = SentenceTransformer('all-MiniLM-L6-v2')
        self.graph = graph
        self.documents = []
        self.metadata = []
        self.embeddings = None
        self.cache_file = cache_file
        
        self.client = genai.Client(api_key=api_key)

        self._build_index()

    def _build_index(self):
        if os.path.exists(self.cache_file):
            print(f"Loading index from {self.cache_file}...")
            with open(self.cache_file, 'rb') as f:
                data = pickle.load(f)
                self.documents = data['documents']
                self.metadata = data['metadata']
                self.embeddings = data['embeddings']
            return
        
        temp_docs = []
        temp_meta = []

        # ==============================================================================
        # 1. LES TOURS (Offres Commerciales + Géographie liée)
        # ==============================================================================
        query_tours = """
        PREFIX cs: <http://data.cyclingtour.fr/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        
        SELECT ?tour ?label ?price ?duration ?guideName
        WHERE {
            ?tour a cs:TourPackage ;
                  rdfs:label ?label ;
                  cs:pricePerDayTour ?price ;
                  cs:duration ?duration .
            OPTIONAL { ?tour cs:guideAssigned ?g . ?g foaf:name ?guideName }
        }
        """
        for row in self.graph.query(query_tours):
            tour_uri = row['tour']
            
            q_details = """
            PREFIX cs: <http://data.cyclingtour.fr/schema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?stageLabel ?difficulty ?elevation ?mountainLabel WHERE {
                ?tour cs:includesStage ?stage .
                ?stage rdfs:label ?stageLabel ;
                       cs:stagePath ?path .
                ?path cs:difficulty ?difficulty ;
                      cs:elevationGain ?elevation .
                OPTIONAL { 
                    ?path cs:includesMountain ?mnt . 
                    ?mnt rdfs:label ?mountainLabel 
                }
            }
            """
            details = self.graph.query(q_details, initBindings={'tour': tour_uri})
            
            stages_txt = []
            mountains = set()
            total_difficulty = "Modéré"
            
            for d in details:
                stages_txt.append(f"{d['stageLabel']} (Dénivelé: {d['elevation']}m)")
                if d['mountainLabel']: mountains.add(str(d['mountainLabel']))
                if "VeryHard" in str(d['difficulty']): 
                    total_difficulty = "Très Difficile / Haute Montagne"
                elif "Hard" in str(d['difficulty']):
                    total_difficulty = "Difficile"
            
            full_text = (
                f"Offre Touristique: {row['label']}. "
                f"Niveau global: {total_difficulty}. "
                f"Prix: {row['price']}€/jour. Durée: {row['duration']}. "
                f"Guide responsable: {row['guideName']}. "
                f"Étapes du parcours: {', '.join(stages_txt)}. "
                f"Cols et Montagnes traversés: {', '.join(mountains)}."
            )
            
            temp_docs.append(full_text)
            temp_meta.append({'uri': str(tour_uri), 'type': 'Tour', 'context': full_text})

        # ==============================================================================
        # 2. LES CHEMINS (Détails techniques géographiques)
        # ==============================================================================
        query_paths = """
        PREFIX cs: <http://data.cyclingtour.fr/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?path ?label ?diff ?elev WHERE {
            ?path a cs:Path ;
                  rdfs:label ?label ;
                  cs:difficulty ?diff ;
                  cs:elevationGain ?elev .
        }
        """
        for row in self.graph.query(query_paths):
            q_mnt = """
            PREFIX cs: <http://data.cyclingtour.fr/schema#>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?mLabel ?mElev WHERE {
                ?path cs:includesMountain ?m .
                ?m rdfs:label ?mLabel ;
                   cs:elevation ?mElev .
            }
            """
            mnts = self.graph.query(q_mnt, initBindings={'path': row['path']})
            mnt_txt = [f"{m['mLabel']} ({m['mElev']}m)" for m in mnts]
            
            difficulty_str = str(row['diff']).split('#')[-1]
            
            full_text = (
                f"Itinéraire / Chemin: {row['label']}. "
                f"Difficulté technique: {difficulty_str}. Dénivelé positif: {row['elev']}m. "
                f"Liste des cols inclus: {', '.join(mnt_txt) if mnt_txt else 'Aucun col majeur'}."
            )
            temp_docs.append(full_text)
            temp_meta.append({'uri': str(row['path']), 'type': 'Path', 'context': full_text})

        # ==============================================================================
        # 3. LES VÉLOS
        # ==============================================================================
        query_bikes = """
        PREFIX cs: <http://data.cyclingtour.fr/schema#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?bike ?label ?status ?price ?comment ?type WHERE {
            ?bike a ?type ;
                  rdfs:label ?label ;
                  cs:maintenanceStatus ?status ;
                  cs:pricePerDayBike ?price .
            OPTIONAL { ?bike rdfs:comment ?comment }
            FILTER(?type != cs:Bike) 
        }
        """
        for row in self.graph.query(query_bikes):
            status = str(row['status']).split('#')[-1]
            bike_type = str(row['type']).split('#')[-1]
            
            full_text = (
                f"Vélo disponible à la location: {row['label']}. "
                f"Catégorie: {bike_type}. "
                f"Statut Maintenance: {status}. "
                f"Prix location: {row['price']}€/jour. "
                f"Description technique: {row['comment']}."
            )
            temp_docs.append(full_text)
            temp_meta.append({'uri': str(row['bike']), 'type': 'Bike', 'context': full_text})

        # ==============================================================================
        # 4. AVIS CLIENTS
        # ==============================================================================
        query_reviews = """
        PREFIX cs: <http://data.cyclingtour.fr/schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?clientName ?bikeLabel ?rating ?text WHERE {
            ?review a cs:Review ;
                    cs:reviewText ?text ;
                    cs:rating ?rating ;
                    cs:reviewedBy ?client ;
                    cs:reviewsItem ?bike .
            ?client foaf:name ?clientName .
            ?bike rdfs:label ?bikeLabel .
        }
        """
        for row in self.graph.query(query_reviews):
            full_text = (
                f"Avis Client: Le client {row['clientName']} a noté le vélo '{row['bikeLabel']}' "
                f"{row['rating']}/5. Commentaire du client: {row['text']}"
            )
            temp_docs.append(full_text)
            temp_meta.append({'uri': 'review', 'type': 'Review', 'context': full_text})

        # ==============================================================================
        # 5. RÉSERVATIONS
        # ==============================================================================
        query_bookings = """
        PREFIX cs: <http://data.cyclingtour.fr/schema#>
        PREFIX foaf: <http://xmlns.com/foaf/0.1/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?clientName ?bikeLabel ?dateStart ?dateEnd WHERE {
            ?booking a cs:BikeBooking ;
                     cs:bookedBy ?client ;
                     cs:bikeBooked ?bike ;
                     cs:bookingDate ?dateStart ;
                     cs:endDate ?dateEnd .
            ?client foaf:name ?clientName .
            ?bike rdfs:label ?bikeLabel .
        }
        """
        for row in self.graph.query(query_bookings):
            full_text = (
                f"Réservation: Le client {row['clientName']} a réservé le vélo '{row['bikeLabel']}' "
                f"du {row['dateStart']} au {row['dateEnd']}."
            )
            temp_docs.append(full_text)
            temp_meta.append({'uri': 'booking', 'type': 'Booking', 'context': full_text})

        self.documents = temp_docs
        self.metadata = temp_meta

        if self.documents:
            self.embeddings = self.model.encode(self.documents, convert_to_tensor=True)

        with open(self.cache_file, 'wb') as f:
            pickle.dump({
                'documents': self.documents,
                'metadata': self.metadata,
                'embeddings': self.embeddings
            }, f)

    def search(self, user_query, top_k=3):
        if self.embeddings is None or not self.documents:
            return []

        query_embedding = self.model.encode(user_query, convert_to_tensor=True)
        if self.embeddings.device != query_embedding.device:
            query_embedding = query_embedding.to(self.embeddings.device)
            
        scores = util.cos_sim(query_embedding, self.embeddings)[0]
        top_results = torch.topk(scores, k=min(top_k, len(self.documents)))

        results = []
        for score, idx in zip(top_results.values, top_results.indices):
            idx = int(idx)
            results.append(self.metadata[idx])
            
        return results

    def ask_gemini(self, user_query):
        retrieved_docs = self.search(user_query)
        context_str = "\n".join([doc['context'] for doc in retrieved_docs])
        
        print("Context for Gemini:\n", context_str)

        prompt = f"""
        Tu es l'assistant opérationnel intelligent de "Cycling Tour", une agence de cyclotourisme. Ta base de connaissances ne se limite pas aux vélos, elle couvre l'ensemble de l'écosystème de l'agence.

        Tu as accès à des données précises concernant :
        1.  **Le Parcours & Terrain** : Les itinéraires (Paths), les étapes, les cols de montagne (altitude, difficulté).
        2.  **L'Offre Commerciale** : Les packages touristiques complets (prix, durée, guides assignés) et le catalogue de vélos (prix/jour, statut de maintenance, type : électrique, route, cargo, etc.).
        3.  **La Gestion Client** : Les profils clients, leurs réservations passées et futures, et les avis détaillés qu'ils ont laissés sur le matériel.
        4.  **L'Équipe** : Les guides touristiques et leurs coordonnées.

        Instructions pour répondre :
        - **Synthétise** : Ne donne pas juste une info isolée. Si on te demande un vélo, vérifie s'il est disponible, s'il a de bons avis, et s'il est adapté aux tours proposés.
        - **Croise les données** : Relie les clients aux réservations, les guides aux tours, et les difficultés des montagnes aux capacités des vélos.
        - **Justifie** : Appuie chaque affirmation par un fait explicite du contexte (ex: "Ce tour est difficile car il inclut le Col du Galibier à 2642m").

        Utilise le contexte suivant pour répondre :
        {context_str}

        Question : {user_query}
        """
        
        response = self.client.models.generate_content(
            model='gemini-2.5-flash-lite',
            contents=prompt
        )
        return response.text
