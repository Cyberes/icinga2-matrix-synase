from prometheus_client.parser import text_string_to_metric_families


def parse_metrics(families):
    output = {}
    for family in text_string_to_metric_families(families):
        output[family.name] = {}
        for sample in family.samples:
            if sample.name not in output[family.name].keys():
                output[family.name][sample.name] = []
            output[family.name][sample.name].append(sample)
    return output
