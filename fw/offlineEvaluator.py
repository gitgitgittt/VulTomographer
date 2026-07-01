import re
import Levenshtein
from codebleu import calc_codebleu


class OfflineEvaluator:

    @staticmethod
    def evaluate_context_reconstruction(generated_context: str, ground_truth_context: str) -> dict:

        if not generated_context or not ground_truth_context:
            return {"Levenshtein_Similarity": 0.0, "CodeBLEU": 0.0}

        distance = Levenshtein.distance(generated_context, ground_truth_context)
        max_len = max(len(generated_context), len(ground_truth_context))
        levenshtein_sim = 1.0 - (distance / max_len) if max_len > 0 else 1.0

        try:

            codebleu_result = calc_codebleu(
                references=[ground_truth_context],
                predictions=[generated_context],
                lang="c"
            )
            codebleu_score = codebleu_result['codebleu']
        except Exception as e:
            print(f"CodeBLEU calculation error: {e}")
            codebleu_score = 0.0

        return {
            "Levenshtein_Similarity": levenshtein_sim,
            "CodeBLEU": codebleu_score
        }

    @staticmethod
    def extract_symbols(code_expr: str) -> set:

        symbols = set(re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', code_expr))
        keywords = {
            'if', 'else', 'return', 'sizeof', 'int', 'char', 'void', 'struct',
            'unsigned', 'LENGTH', 'SIZE', 'NULL', 'true', 'false'
        }
        return symbols - keywords

    @staticmethod
    def evaluate_specification_mining(generated_constraint: str, ground_truth_patch_expr: str) -> dict:

        gen_symbols = OfflineEvaluator.extract_symbols(generated_constraint)
        gt_symbols = OfflineEvaluator.extract_symbols(ground_truth_patch_expr)

        if not gt_symbols:
            symbol_recall = 1.0 if not gen_symbols else 0.0
        else:
            correct_symbols = gen_symbols.intersection(gt_symbols)
            symbol_recall = len(correct_symbols) / len(gt_symbols)

        gen_tokens = set(re.findall(r'\w+|[^\s\w]+', generated_constraint))
        gt_tokens = set(re.findall(r'\w+|[^\s\w]+', ground_truth_patch_expr))

        intersection = len(gen_tokens.intersection(gt_tokens))
        union = len(gen_tokens.union(gt_tokens))
        ncs_score = intersection / union if union > 0 else 1.0

        return {
            "Symbol_Recall": symbol_recall,
            "NCS": ncs_score
        }

if __name__ == "__main__":
    evaluator = OfflineEvaluator()



    res_context = evaluator.evaluate_context_reconstruction(pred_context, real_context)
    print(f"Levenshtein: {res_context['Levenshtein_Similarity']:.4f}")
    print(f"CodeBLEU: {res_context['CodeBLEU']:.4f}")


    res_constraint = evaluator.evaluate_specification_mining(pred_expr, real_patch_expr)
    print(f"Symbol Recall: {res_constraint['Symbol_Recall']:.4f}")
    print(f"NCS: {res_constraint['NCS']:.4f}")
