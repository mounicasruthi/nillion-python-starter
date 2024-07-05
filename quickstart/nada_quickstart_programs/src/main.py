from nada_dsl import *

def initialize_parties(nr_parties):
    return [Party(name=f"Party{i}") for i in range(nr_parties)]

def inputs_initialization(nr_parties, nr_criteria, parties):
    feedbacks = []
    for c in range(nr_criteria):
        criteria_feedbacks = []
        for p in range(nr_parties):
            feedback_input = SecretUnsignedInteger(Input(name=f"p{p}_c{c}", party=parties[p]))
            role_input = SecretUnsignedInteger(Input(name=f"role{p}_c{c}", party=parties[p]))
            criteria_feedbacks.append(feedback_input * role_input)
        feedbacks.append(criteria_feedbacks)
    return feedbacks

def advanced_computation(feedbacks, weights):
    total = UnsignedInteger(0)
    for feedback, weight in zip(feedbacks, weights):
        total += feedback * weight
    return total

def weighted_bonus_allocation(nr_parties, nr_criteria, weighted_feedbacks, weights, outparty):
    results = []
    for c in range(nr_criteria):
        total = advanced_computation(weighted_feedbacks[c], weights[c])
        results.append((total, c))
    
    # Sort results in descending order by total feedback score
    sorted_results = sorted(results, key=lambda x: x[0], reverse=True)
    
    # Create Output objects in sorted order
    output_results = [Output(total, name=f"final_bonus_allocation_c{c}", party=outparty) for total, c in sorted_results]
    
    return output_results

def nada_main():
    nr_parties = 5
    nr_criteria = 3
    outparty = Party(name="OutParty")

    parties = initialize_parties(nr_parties)
    feedbacks_per_criteria = inputs_initialization(nr_parties, nr_criteria, parties)

    # Initialize weights for each criteria
    weights = [
        [SecretUnsignedInteger(Input(name=f"weight{p}_c{c}", party=parties[p])) for p in range(nr_parties)]
        for c in range(nr_criteria)
    ]

    results = weighted_bonus_allocation(nr_parties, nr_criteria, feedbacks_per_criteria, weights, outparty)

    return results
