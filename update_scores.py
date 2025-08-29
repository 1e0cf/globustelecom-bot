import json

src = "qa1_scores.json"
dest = "qa1.json"
output = "qa1_updated.json"

with open(src, 'r', encoding='utf-8') as f:
    src_data = json.load(f)

with open(dest, 'r', encoding='utf-8') as f:
    dest_data = json.load(f)

total_scores_sum = 0
question_count = 0
scores_map = {}

for question_pair in src_data["questions"]:
    for item in question_pair:
        total_score = sum(item["scores"].values())
        item["total_score"] = total_score
        total_scores_sum += total_score
        question_count += 1
        scores_map[item["question"]] = {
            "scores": item["scores"],
            "total_score": item["total_score"]
        }

average_score = total_scores_sum / question_count if question_count > 0 else 0
src_data["average_score"] = average_score
dest_data["average_score"] = average_score

for question_pair in dest_data["questions"]:
    for item in question_pair:
        if item["question"] in scores_map:
            item["scores"] = scores_map[item["question"]]["scores"]
            item["total_score"] = scores_map[item["question"]]["total_score"]

with open(output, 'w', encoding='utf-8') as f:
    json.dump(dest_data, f, ensure_ascii=False, indent=4)

print(f"File '{output}' has been created successfully.")