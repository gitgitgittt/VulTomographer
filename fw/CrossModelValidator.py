import re
from openai import OpenAI
import concurrent.futures

client = OpenAI(
    api_key="",
    base_url=""
)


class CrossModelValidator:
    def __init__(self):

        self.auditor_models = ["gpt-3.5-turbo", "gpt-4o", "gemini-3.1-flash", "deepseek-r1"]

    def _call_judge(self, model: str, prompt: str) -> bool:

        try:
            response = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=model,
                temperature=0.0,
                max_tokens=10
            )
            reply = response.choices[0].message.content.strip().upper()


            if reply.startswith("YES") or "VALID" in reply or "TRUE" in reply:
                return True
            return False
        except Exception as e:
            print(f"[Judge Error] {model} failed: {e}")
            return False

    def get_consensus(self, prompt: str) -> bool:

        votes = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures = {executor.submit(self._call_judge, model, prompt): model for model in self.auditor_models}
            for future in concurrent.futures.as_completed(futures):
                votes.append(future.result())
        return all(votes)

    def check_context_reconstruction(self, code: str, generated_context: str) -> bool:
        prompt = f"""You are a strict C/C++ compiler auditor. 
Review the following original code and the generated header context.
Does the generated context logically define the undefined symbols without violating objective C/C++ syntax rules?
Answer ONLY with 'YES' or 'NO'.

Code: ```c\n{code}\n```
Generated Context: ```c\n{generated_context}\n```"""
        return self.get_consensus(prompt)

    def check_specification_mining(self, commit: str, code: str, generated_constraint: str) -> bool:
        prompt = f"""You are a strict Security Specification Auditor.
Review the developer's commit message, the code snippet, and the extracted formal safety constraint.
Does the extracted constraint accurately reflect the developer's corrective intent without semantic divergence?
Answer ONLY with 'YES' or 'NO'.

Commit: {commit}
Code: ```c\n{code}\n```
Generated Constraint: {generated_constraint}"""
        return self.get_consensus(prompt)

    def check_trace_execution(self, code: str, context: str, trace: str) -> bool:
        prompt = f"""You are a strict Neural Symbolic Executor Auditor.
Review the code, its execution context, and the simulated abstract execution trace.
Do the variable lifecycle transitions and loop summaries strictly adhere to standard C/C++ programming semantics and represent a physically viable exploit path?
Answer ONLY with 'YES' or 'NO'.

Context: ```c\n{context}\n```
Code: ```c\n{code}\n```
Simulated Trace: {trace}"""
        return self.get_consensus(prompt)

if __name__ == "__main__":
    validator = CrossModelValidator()

    test_set_results = [
        {
        },
    ]

    stats = {"context_pass": 0, "constraint_pass": 0, "trace_pass": 0, "total": len(test_set_results)}

    print("Starting Cross-Model Consistency Check on Test Set...")
    for i, sample in enumerate(test_set_results):
        print(f"\nEvaluating Sample {i + 1}/{len(test_set_results)}")

        if validator.check_context_reconstruction(sample["code"], sample["gen_context"]):
            stats["context_pass"] += 1

        if validator.check_specification_mining(sample["commit"], sample["code"], sample["gen_constraint"]):
            stats["constraint_pass"] += 1

        if validator.check_trace_execution(sample["code"], sample["gen_context"], sample["gen_trace"]):
            stats["trace_pass"] += 1

    print("\n=== Final Consensus Rates ===")
    print(f"Phase 1 (Context):    {stats['context_pass'] / stats['total'] * 100:.1f}%")
    print(f"Phase 2 (Constraint): {stats['constraint_pass'] / stats['total'] * 100:.1f}%")
    print(f"Phase 3 (Trace):      {stats['trace_pass'] / stats['total'] * 100:.1f}%")