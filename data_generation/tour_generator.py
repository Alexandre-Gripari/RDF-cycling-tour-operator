import random
from rdflib import Graph, Namespace, Literal, RDF, URIRef
from rdflib.namespace import XSD, RDFS, FOAF

INPUT_FOLDER = "database/"
INPUT_FILES = ["cto_mountains_paths.ttl", "cto_data_guides.ttl"]
INPUT_FILES = [INPUT_FOLDER + f for f in INPUT_FILES]
OUTPUT_FILE = "cto_data_tour.ttl"

CTO = Namespace("http://data.cyclingtour.fr/data#")
CS = Namespace("http://data.cyclingtour.fr/schema#")
DBP = Namespace("http://dbpedia.org/resource/")

def get_available_guides(graph):
    guides = []
    for guide_uri in graph.subjects(RDF.type, CS.Guide):
        guides.append(guide_uri)

    return list(set(guides))

def generate_duration(km):
    try:
        val = float(km)
        hours = int(val / 22) + 1 
        return Literal(f"PT{hours}H", datatype=XSD.duration)
    except:
        return Literal("PT6H", datatype=XSD.duration)

def main():
    g = Graph()
    for file in INPUT_FILES:
        g.parse(file, format="turtle")
        print(f"   -> {file} chargé.")

    available_guides = get_available_guides(g)

    out_g = Graph()
    for prefix, namespace in g.namespaces():
        out_g.bind(prefix, namespace)
    out_g.bind("cto", CTO)
    out_g.bind("cs", CS)

    adj_list = {}

    stage_count = 0
    
    for path_uri in g.subjects(RDF.type, CS.Path):
        if not isinstance(path_uri, URIRef): continue

        start_node = g.value(path_uri, CS.hasStart)
        end_node = g.value(path_uri, CS.hasEnd)
        length = g.value(path_uri, CS.length)
        
        path_label = g.value(path_uri, RDFS.label)
        if not path_label:
            path_label = Literal(f"Trajet {path_uri.split('#')[-1]}")

        path_id = path_uri.split("#")[-1].replace("_Path", "")
        stage_uri = CTO[f"Stage_{path_id}"]

        selected_guide = random.choice(available_guides)

        out_g.add((stage_uri, RDF.type, CS.TourStage))
        out_g.add((stage_uri, RDFS.label, Literal(f"Stage: {path_label}")))
        out_g.add((stage_uri, CS.stagePath, path_uri))
        out_g.add((stage_uri, CS.guideAssigned, selected_guide)) 
        out_g.add((stage_uri, CS.tourCapacity, Literal(10)))
        
        if length:
            out_g.add((stage_uri, CS.duration, generate_duration(length)))

        if start_node and end_node:
            if start_node not in adj_list: adj_list[start_node] = []
            adj_list[start_node].append({
                "stage": stage_uri,
                "end": end_node,
                "length": float(length) if length else 100
            })
            stage_count += 1

    pkg_count = 0
    
    for start_city in adj_list.keys():
        current_city = start_city
        chain = []
        
        steps_target = random.randint(3, 5)
        
        for _ in range(steps_target):
            if current_city in adj_list:
                step = random.choice(adj_list[current_city])
                chain.append(step)
                current_city = step['end']
            else:
                break
        
        if len(chain) >= 3:
            pkg_id = f"Package_{chain[0]['stage'].split('#')[-1].replace('Stage_', '')}_Tour"
            pkg_uri = CTO[pkg_id]
            
            main_guide = g.value(chain[0]['stage'], CS.guideAssigned) or random.choice(available_guides)
            
            out_g.add((pkg_uri, RDF.type, CS.TourPackage))
            out_g.add((pkg_uri, RDFS.label, Literal(f"Tour Package: Start at {start_city.split('/')[-1]}")))
            out_g.add((pkg_uri, CS.guideAssigned, main_guide))
            out_g.add((pkg_uri, CS.pricePerDayTour, Literal(120.0 * len(chain), datatype=XSD.decimal)))
            
            total_km = sum([s['length'] for s in chain])
            total_hours = int(total_km / 18)
            out_g.add((pkg_uri, CS.duration, Literal(f"PT{total_hours}H", datatype=XSD.duration)))

            for step in chain:
                out_g.add((pkg_uri, CS.includesStage, step['stage']))
            
            pkg_count += 1

    out_g.serialize(destination=OUTPUT_FILE, format="turtle")

if __name__ == "__main__":
    main()
