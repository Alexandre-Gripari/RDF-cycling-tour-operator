from rdflib import Graph


def get_rdf_data_summary(graph):
    summary = "### DATA SAMPLES & STRUCTURE\n"
    summary += "Here is a summary of the Classes and Properties found in the actual RDF data, with examples:\n\n"

    query_classes = """
    SELECT DISTINCT ?type WHERE {
        ?s a ?type .
    }
    """
    classes = graph.query(query_classes)
    for row_c in classes:
        class_uri = str(row_c.type)
        if "www.w3.org" in class_uri and "schema.org" not in class_uri:
            pass
        summary += f"#### Class: <{class_uri}>\n"
        query_props = f"""
        SELECT DISTINCT ?p WHERE {{
            ?s a <{class_uri}> .
            ?s ?p ?o .
        }}
        """

        properties = graph.query(query_props)
        if not properties:
            summary += "  (No properties found for instances of this class)\n"
            continue

        for row_p in properties:
            prop_uri = str(row_p.p)
            query_samples = f"""
            SELECT ?o WHERE {{
                ?s a <{class_uri}> .
                ?s <{prop_uri}> ?o .
            }} LIMIT 3
            """

            samples = graph.query(query_samples)
            sample_vals = []
            for s_row in samples:
                val = str(s_row.o)
                val = val.replace("\n", " ").strip()
                if len(val) > 50:
                    val = val[:47] + "..."
                sample_vals.append(val)

            vals_str = ", ".join([f"'{v}'" for v in sample_vals])
            prop_name = (
                prop_uri.split("#")[-1] if "#" in prop_uri else prop_uri.split("/")[-1]
            )
            summary += f"  - **{prop_name}** (<{prop_uri}>): [{vals_str}]\n"
        summary += "\n"
    return summary
