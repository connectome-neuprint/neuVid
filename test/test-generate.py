import argparse
import datetime
import os
import sys
import time

sys.path.append(os.path.normpath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "../neuVid")))
from utilsGeneral import report_version
from gen import generate, generate_single_step, get_raw_training_doc

def get_log_filename(argv, model, single_step, output_dir):
    script = os.path.splitext(os.path.basename(sys.argv[0]))[0]
    t = datetime.datetime.now()
    t = t.replace(microsecond=0)
    steps = "single" if single_step else "multi"
    name = f"{script}-results_{model}_{steps}_{t}.txt"
    name = name.replace(" ", "_")
    name = name.replace(":", "-")
    path = os.path.join(output_dir, name)
    return path

def log(s, path):
    print(s)
    with open(path, "a") as f:
        f.write(s + "\n")

def model_vendor(model):
    if model.startswith("gpt"):
        return "OpenAI"
    elif model.startswith("claude"):
        return "Anthropic"
    else:
        return None

def vendor_token_keys(vendor):
    if vendor == "OpenAI":
        input_tokens_key = "prompt_tokens"
        output_tokens_key = "completion_tokens"
    elif vendor == "Anthropic":
        input_tokens_key = "input_tokens"
        output_tokens_key = "output_tokens"
    else:
        input_tokens_key = None
        output_tokens_key = None
    return (input_tokens_key, output_tokens_key)

def remove_comments(s):
    lines = s.split("\n")
    result = ""
    for line in lines:
        if not line.lstrip().startswith("#"):
            result += line + "\n"
    return result

def get_tests(s):
    result = s.split("===\n")
    return result

def get_test_parts(s):
    raw_parts = s.split("---\n")
    result = []
    for raw_part in raw_parts:
        raw_part_lines = raw_part.split("\n")
        # Remove blank lines.
        part_lines = [line for line in raw_part_lines if line]
        part = "\n".join(part_lines)
        result.append(part)
    return result

def run_test(test, raw_doc, api_key, models, temperature, pause, log_file, time_start, cumulative_cost, last, single_step):
    parts = get_test_parts(test)
    previous_result = ""
    for i in range(len(parts)):
        part = parts[i]
    
        user_request = part
        log(user_request, log_file)

        if single_step:
            result = generate_single_step(raw_doc, previous_result, user_request, api_key, models, temperature)
        else:
            result = generate(raw_doc, previous_result, user_request, api_key, models, temperature)

        if result["ok"]:
            generated_json = result["generated_json"]
            log(generated_json, log_file)

            previous_result = generated_json

            vendor = model_vendor(models[0])
            input_tokens_key, output_tokens_key = vendor_token_keys(vendor)

            if single_step:
                usage = result["usage"]
                input_tokens = usage[input_tokens_key]
                output_tokens = usage[output_tokens_key]
                total_tokens = usage["total_tokens"] if "total_tokens" in usage else input_tokens + output_tokens
                log(f"Tokens: prompt {input_tokens}, completion {output_tokens}, total {total_tokens}", log_file)

            else:
                usage1 = result["usage1"]
                input_tokens1 = usage1[input_tokens_key]
                output_tokens1 = usage1[output_tokens_key]
                total_tokens1 = usage1["total_tokens"] if "total_tokens" in usage1 else input_tokens1 + output_tokens1
                log(f"Step 1 tokens: prompt {input_tokens1}, completion {output_tokens1}, total {total_tokens1}", log_file)

                usage2 = result["usage2"]
                input_tokens2 = usage2[input_tokens_key]
                output_tokens2 = usage2[output_tokens_key]
                total_tokens2 = usage2["total_tokens"] if "total_tokens" in usage2 else input_tokens2 + output_tokens2
                log(f"Step 2 tokens: prompt {input_tokens2}, completion {output_tokens2}, total {total_tokens2}", log_file)

                usage3 = result["usage3"]
                input_tokens3 = usage3[input_tokens_key]
                output_tokens3 = usage3[output_tokens_key]
                total_tokens3 = usage3["total_tokens"] if "total_tokens" in usage3 else input_tokens3 + output_tokens3
                log(f"Step 3 tokens: prompt {input_tokens3}, completion {output_tokens3}, total {total_tokens3}", log_file)

                total_tokens = total_tokens1  + total_tokens2 + total_tokens3
                log(f"Total tokens for all steps: {total_tokens}", log_file)

            time_now = datetime.datetime.now()
            cumulative_time = (time_now - time_start).seconds
            cost = result["cost_USD"]
            cumulative_cost += cost
            log(f"Cumulative time {cumulative_time} secs, cost ${cumulative_cost:.2f}\n",  log_file)
        else:
            log(result["error"], log_file)

        if not last:
            time.sleep(pause)

    return cumulative_cost

if __name__ == "__main__":
    neuVid_version = report_version()
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", help="path to the input file of test requests")
    # By default, print output.
    parser.set_defaults(output="/tmp")
    parser.add_argument("--output", "-o", help="path to the output directory for the output log file")
    parser.set_defaults(api_key="")
    parser.add_argument("--apikey", "-a", dest="api_key", help="API key")
    parser.set_defaults(model="gpt-4")
    parser.add_argument("--model", "-m", help="model name")
    parser.set_defaults(temperature=0)
    parser.add_argument("--temperature", "-t", type=float, help="model temperature")
    parser.set_defaults(pause=30)
    parser.add_argument("--pause", "-p", type=int, help="pause between OpenAI API calls")
    parser.set_defaults(single_step=False)
    parser.add_argument("--single", dest="single_step", action="store_true", help="use a single step (requires a big context)")
    args = parser.parse_args()

    time_start = datetime.datetime.now()

    log_file = get_log_filename(sys.argv, args.model, args.single_step, args.output)
    print(f"Log file: {log_file}")

    log(f"neuVid version: {neuVid_version}", log_file)
    log(f"Input: {args.input}", log_file)
    log(f"Temperature: {args.temperature}", log_file)
    log(f"Pause: {args.pause} secs", log_file)

    raw_doc_data = get_raw_training_doc()
    if not raw_doc_data["ok"]:
        print(raw_doc_data["error"])
        sys.exit()

    log(f"Training document: {raw_doc_data['source']}", log_file)
    log(f"Training document version: {raw_doc_data['version']}", log_file)
    raw_doc = raw_doc_data["text"]

    models = [args.model, args.model, args.model]
    log(f"Models: {models}", log_file)
    log(f"Single step: {args.single_step}\n", log_file)

    vendor = model_vendor(args.model)
    api_key = args.api_key 
    if not api_key:
        if vendor == "OpenAI":
            api_key = os.getenv("OPENAI_API_KEY")
        elif vendor == "Anthropic":
            api_key = os.getenv("ANTHROPIC_API_KEY")

    with open(args.input, "r") as f:
        s = f.read()
    s = remove_comments(s)
    tests = get_tests(s)

    cost = 0
    for i in range(len(tests)):
        test = tests[i]
        log("===============", log_file)
        log(f"Test {i+1} of {len(tests)}:\n", log_file)
        last = (i == len(tests) - 1)
        cost = run_test(test, raw_doc, api_key, models, args.temperature, args.pause, log_file, time_start, cost, last, args.single_step)
