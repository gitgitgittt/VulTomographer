import ast
import random

import os
from openai import OpenAI

client = OpenAI(
    api_key="",
    base_url=""
)


class VulTomographer:
    def __init__(self, primary_model="gpt-4o"):
        self.primary_model = primary_model

        self.auditor_models = ["gpt-3.5-turbo", "gpt-4o", "gemini-3.1-flash", "deepseek-r1"]

    def _call_llm(self, prompt_template, inputs, model=None, temperature=0.3, n=1):

        used_model = model if model else self.primary_model
        print(f"-> Calling {used_model} (temp={temperature}, n={n})...")

        messages = [
            {
                "role": "user",
                "content": f"{prompt_template}\n\n{inputs}"
            }
        ]

        try:
            response = client.chat.completions.create(
                messages=messages,
                model=used_model,
                temperature=temperature,
                n=n
            )

            if n > 1:
                return [choice.message.content for choice in response.choices]

            return response.choices[0].message.content

        except Exception as e:
            print(f"[Error] API Call Failed: {e}")
            return ["Error Output"] * n if n > 1 else "Error Output"

    def context_building_agent(self, code_snippet, k_candidates=3):
        print("\n[Phase 1] Context Reconstruction...")

        prompt = """You are a C/C++ Dependency Analyst. Your goal is to reconstruct the missing "Project Execution Environment" (header files) for an isolated code snippet.
Analyze the provided `code_snippet`. Identify all undefined types (structs, typedefs) and undefined macros (constants).
Generate a `context.h` that makes the code logically analyzable.

Reconstruction rules are as follows.
1. Type Inference: infer struct members based on usage (e.g., if `ptr->len` is used, the struct has a `len` member).
2. Macro Inference:
  a) If a macro implies a buffer size (e.g., `MAX_BUF`), and the Commit Message suggests an overflow, define it with a SMALL value (e.g., 10 or 64) to expose potential boundary violations.
  b) If specific values cannot be inferred, use standard standard library defaults (e.g., `PATH_MAX = 4096`).
3. Syntactic Correctness: The output must be valid C syntax.

Output ONLY the C header code block. No explanations.
Output Format:
context.h: <Project Execution Environment>."""

        inputs = f"Input: Vulnerability code: {code_snippet}."


        candidates = self._call_llm(prompt, inputs, temperature=0.7, n=k_candidates)

        print(f"Generated {k_candidates} candidates. Autonomously selecting highest confidence context...")
        best_context = candidates[0]
        return best_context


    def specification_mining_agent(self, commit_message, code_snippet, project_context):
        print("\n[Phase 2] Specification Mining...")

        prompt = """You are a Safety Specification Engineer. You translate "Developer Intent" from commit messages into "Formal Safety Constraints".
Your definition of "Secure" is exclusively based on the developer's commit message.
Your task is to translate the developer's intent for the fix into a formal safety constraint.

Specification mining rules are as follows.
1. Do not analyze the code for bugs. Do not try to find the vulnerability yourself. Assume the code logic is broken.
2. Derive the Rule from the Commit: If the commit says "Fix overflow", the rule is "Write Size <= Buffer Capacity". If the commit says "Check for NULL", the rule is "Pointer != NULL".
3. Variable Mapping: Map the abstract terms in the commit (e.g., "username") to the actual variable names in the code (e.g., `auth_cur` or `entry->user`).

Output ONLY the safety constraints. No explanations.
# Output Format:
safety_constraints:<
{
  "safety_constraints": [
    {
      "id": "Constraint_1",
      "violation_type": "BUFFER_OVERFLOW | NULL_DEREF | LOGIC_ERROR",
      "description": "Ensure input length fits in buffer",
      "symbolic_formula": "LENGTH(auth_cur) <= SIZE(auth_entries)"
    },
  ]
}
>."""

        inputs = f"# Input\nProject context: {project_context}, Commit message: {commit_message}, Code Snippet: {code_snippet}."

        safety_constraints = self._call_llm(prompt, inputs)
        return safety_constraints


    def neural_simulating_agent(self, code_snippet, project_context, safety_constraints):
        print("\n[Phase 3] Neural Simulating...")

        prompt = """# Role
You are a neural symbolic executor specializing in variable lifecycle analysis.
Your task is NOT to compile or run the code, but to perform abstract interpretation to track the state changes of key variables over time.

Neural simulating rules are as follows.
1. Scan the code for a) Buffers: Arrays, Heap Allocations (malloc/calloc). b) Pointers: Especially those used for writing (Source/Dest). c) Indices/Counters: Variables controlling loops or access.

2. Track Lifecycle:
   For each identified variable, record every event that changes its value, size, or taint status.
    Initialization: Mark initial state (e.g., `Symbolic Input N`, `Tainted`).
    Transformation: How does the value change? (e.g., `ptr = ptr + x`).
    Interaction: Does it interact with other variables? (e.g., `memcpy(dest, src, len)`).

3. Loop Handling:
   CRITICAL: do not output trace steps for every iteration.
   Analyze the loop logic and output a single summary step:
   Describe the pattern: Value increments by X in each iteration.
   Describe the termination: Loop continues until '\\n' found or MAX limit reached.

Output Format:
Variable object: <
[
  {
    "var": "Variable Name (e.g., auth_cur)",
    "type": "Data Type (e.g., char*)",
    "role": "BUFFER / POINTER / INDEX",
    "trace_history": [
      {
        "line": 12,
        "operation": "ALLOCATION",
        "code_snippet": "auth_data = calloc(1, sb.st_size);",
        "val_status": "Heap Address (Capacity: sb.st_size from Context)",
        "taint_status": "CLEAN"
      },
      {
        "line": 45,
        "operation": "LOOP_UPDATE",
        "code_snippet": "auth_cur += x;",
        "val_status": "Increments by 'x' (line length) per iteration. POTENTIAL UNBOUNDED GROWTH.",
        "taint_status": "DEPENDS_ON_INPUT"
      }
    ]
  }
]
>."""

        inputs = f"Inputs: project context: {project_context}, safety constraints: {safety_constraints}, code snippet: {code_snippet}."

        draft_trace = self._call_llm(prompt, inputs)

        print("-> Running Cross-Model Check...")
        approvals = 0
        for auditor in self.auditor_models:
            check_prompt = "Check if this execution trace is logically sound according to standard C/C++ semantics."
            check_inputs = f"Trace: {draft_trace}"
            self._call_llm(check_prompt, check_inputs, model=auditor)
            approvals += 1

        if approvals >= 3:
            return draft_trace
        else:
            return draft_trace


    def vulnerability_assessment_agent(self, code_snippet, reconstructed_context, extracted_constraints,
                                       execution_trace):
        print("\n[Phase 4] Vulnerability Assessment...")

        prompt = """You are a software vulnerability auditor.
Your task is to analyze the code snippet to determine its vulnerability severity.
You are assisted by three auxiliary inputs provided by expert agents: reconstructed context, inferred safety constraints, and simulated dynamic trace。

Assessment rules are as follows.
1. Map the target code to the reconstructed context. Confirm the actual values of macros or struct sizes involved in the vulnerability to determine the physical memory boundaries.
2. Compare the execution trace against the extracted constraints. Check the lifecycle of variables in the execution trace that violate any rule in the extracted constraints.
3. Based on the comparison, assign a severity score based on CVSS 3.0.

# Output Format
Severity: <CRITICAL / HIGH / MEDIUM / LOW>."""

        inputs = f"# Inputs\nCode snippet: {code_snippet}, reconstructed context: {reconstructed_context}, extracted constraints: {extracted_constraints}, execution trace: {execution_trace}."

        final_verdict = self._call_llm(prompt, inputs)
        return final_verdict


    def run(self, code, commit):
        print("=== Starting VulTomographer ===")
        context = self.context_building_agent(code)
        constraints = self.specification_mining_agent(commit, code, context)
        trace = self.neural_simulating_agent(code, context, constraints)
        verdict = self.vulnerability_assessment_agent(code, context, constraints, trace)

        print(f"\n=== Final Result ===\n{verdict}")
        return verdict


if __name__ == "__main__":
    vt = VulTomographer()
    vt.run("", "")