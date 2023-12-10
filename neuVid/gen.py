import argparse
import os
import sys
import time

sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utilsGeneral import report_version

def get_version(raw_doc):
    START = "<!-- VERSION: "
    END = " -->\n"
    version = ""
    i0 = raw_doc.find(START)
    if i0 >= 0:
        i0 += len(START)
        i1 = raw_doc.find(END)
        if i1 >= 0:
            version = raw_doc[i0:i1]
    return version

def split_into_chunks(raw_doc):
    START = "<!-- CHUNK START -->\n"
    END = "<!-- CHUNK END -->\n"
    split_start = raw_doc.split(START)
    result = []
    for sp in split_start:
        split_end = sp.split(END)
        if len(split_end) == 2:
            result.append(split_end[0])
    return result

def get_step_from_chunk(chunk):
    START = "<!-- STEP: "
    END = " -->\n"
    step = "ANY"
    if chunk.startswith(START):
        i1 = len(START)
        i2 = chunk.find(END)
        step = chunk[i1:i2]
        chunk = chunk[i2 + len(END):] 
    return (step, chunk)

def remove_comments_from_chunk(chunk):
    result = ""
    lines = chunk.split("\n")
    for line in lines:
        if not line.startswith("<!--"):
            result += line + "\n"
    return result

def remove_wasted_tokens_from_chunk(chunk):
    result = ""
    lines = chunk.split("\n")
    for line in lines:
        # Each back tick is a token.
        if not line.lstrip().startswith("```"):
            line = line.replace("`", "")
            result += line + "\n"
    return result    

def filter_doc(raw_doc, step):
    candidate_chunks = split_into_chunks(raw_doc)
    chunks = []
    for chunk in candidate_chunks:
        chunk_step, chunk = get_step_from_chunk(chunk)
        chunk = remove_comments_from_chunk(chunk)
        chunk = remove_wasted_tokens_from_chunk(chunk)
        if chunk_step == step or chunk_step == "ANY" or step == "SINGLE":
            chunks.append(chunk)
    return "".join(chunks)

def get_prompt(doc, previous_result, user_request, step):
    # The content of this "system" message seems to have little impact on the output.
    # Others have had mixed results using "system" messages in various ways:
    # https://community.openai.com/t/the-system-role-how-it-influences-the-chat-behavior
    system_content = """
        You generate the input JSON for neuVid. Respond with only that JSON.
    """

    user_content = f"""
        If you don't know, respond with {{}}.
        Generate JSON according to the following request using the following context.
    """

    if step.startswith("1"):
        # Step 1 involves context documentation for only the declarations `"neurons"`, `"rois"`, etc.
        if not previous_result:
            request = f"""
            {user_request}
            """
        else:
            request = f"""
            Start with this JSON: {previous_result} 
            {user_request}
            """
    else:
        # Steps 2 and 3 involve context documentation for only `"animation"`.
        if not previous_result:
            request = f"""
            Make no changes to `"neurons"`, `"rois"`, `"synapses"`.
            {user_request}
            If there is `"rois": [],` or `"rois": {{}},` in the generated JSON then remove it.
            """
        else:
            request = f"""
            Start with this JSON and make no changes to `"neurons"`, `"rois"`, `"synapses"`: {previous_result} 
            {user_request}
            If there is `"rois": [],` or `"rois": {{}},` or `"synapses": []` or `"synapses": {{}}` in the generated JSON then remove it.
            """

    user_content += f"""
        CONTEXT: 
        {doc}
        =========
        REQUEST: 
        {request} 
    """

    prompt = [
        {
            "role": "system",
            "content": system_content  
        },
        {
            "role": "user",
            "content": user_content
        }
    ]

    return prompt

def fix_formatting(s):
    lines = s.split("\n")
    n = 0
    for i in range(len(lines)):
        if len(lines[i]) == 0 or lines[i].isspace():
            n += 1
        else:
            break

    for i in range(n):
        del lines[0]

    # For some reason, the GPT models tend to give a random indent for the opening "{"
    # and then some consistent but extra indenting for the rest of the JSON.
    # So first, get rid of the random indenting for the opening "{".

    for i in range(len(lines)):
        if lines[i].lstrip() == "{":
            lines[i] = "{"
            break

    # Next, find that extra indenting for the lines after that "{".

    min_indent = sys.maxsize
    for line in lines[1:]:
        indent = len(line) - len(line.lstrip())
        min_indent = min(indent, min_indent)

    # Then remove that extra indenting.

    result = lines[0] + "\n"
    for line in lines[1:]:
        result += line[min_indent:] + "\n"

    return result

def copy_animation(s):
    if s:
        lines = s.split("\n")
        lines_copied = []
        copying = False
        for line in lines:
            if not copying:
                if line.lstrip().startswith('"animation": ['):
                    copying = True
            if copying:
                lines_copied.append(line)
                line_stripped = line.lstrip().rstrip()
                if line_stripped.endswith("[]") or line_stripped == "]":
                    return lines_copied
    return ['  "animation": []']

def paste_animation(s, lines_copied):
    lines = s.split("\n")
    lines_after_paste = []
    pasting = False
    for line in lines:
        if not pasting:
            if line.lstrip().startswith('"animation": ['):
                pasting = True
        if pasting:
            line_stripped = line.lstrip().rstrip()
            if line_stripped.endswith("[]") or line_stripped == "]":
                lines_after_paste += lines_copied
                pasting = False               
        else:
            lines_after_paste.append(line)
    after_paste = "\n".join(lines_after_paste)
    return after_paste

def submit_prompt(prompt, api_key, model, temperature, step):
    try:
        import requests
    except:
        print("The 'requests' module is not available. Try running this script with Blender:")
        print("$ blender --background --python gen.py -- <arguments>")
        return { f"ok{step}": False, "error": "Python module 'requests' not found", "code": 0 }

    # https://platform.openai.com/docs/api-reference/chat/create

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    body = {
        "model": model,
        "temperature": temperature,
        "seed": 1,
        "messages": prompt
    }
    url = "https://api.openai.com/v1/chat/completions"

    t0 = time.time()
    try:
        response = requests.post(url=url, headers=headers, json=body)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as err:
        return { f"ok{step}": False, "error": str(err) }
    except requests.exceptions.HTTPError as err:
        err_msg = str(err)
        code = None
        response_json = response.json()
        
        if "error" in response_json:
            error = response_json["error"]
            if "message" in error:
                err_msg += f": {str(error['message'])}"
            if "code" in error:
                code = error["code"]
        if code:
            return { f"ok{step}": False, "error": err_msg, "code": code }
        else:
            return { f"ok{step}": False, "error": err_msg }
    t1 = time.time()
    elapsed_sec = round(t1 - t0)

    response_json = response.json()

    usage = {}
    if "usage" in response_json:
        usage = response_json["usage"]
    
    generated_json = {}
    if "choices" in response_json:
        choices = response_json["choices"]
        if type(choices) == list and len(choices) > 0:
            choice = choices[0]
            if "message" in choice:
                message = choice["message"]
                if "content" in message:
                    generated_json = message["content"]

    generated_json = fix_formatting(generated_json)

    return {
        f"ok{step}": True,
        f"generated_json{step}": generated_json,
        f"elapsed_sec{step}": elapsed_sec,
        f"usage{step}": usage
    }

def compute_cost(usage, model):
    if not "prompt_tokens" in usage or not "completion_tokens" in usage:
        return 0

    prompt_tokens = usage["prompt_tokens"]
    completion_tokens = usage["completion_tokens"]

    cost_per_1k_prompt_tokens = 0
    cost_per_1k_completion_tokens = 0

    # https://openai.com/pricing#language-models
    if model.startswith("gpt-4"):
        if "32k" in model:
            cost_per_1k_prompt_tokens = 0.06
            cost_per_1k_completion_tokens = 0.12
        else:
            cost_per_1k_prompt_tokens = 0.03
            cost_per_1k_completion_tokens = 0.06
    elif model.startswith("gpt-3.5-turbo"):
        if "16k" in model:
            cost_per_1k_prompt_tokens = 0.001
            cost_per_1k_completion_tokens = 0.002
        else:
            cost_per_1k_prompt_tokens = 0.0015
            cost_per_1k_completion_tokens = 0.002

    cost = prompt_tokens / 1000 * cost_per_1k_prompt_tokens + completion_tokens / 1000 * cost_per_1k_completion_tokens
    return cost

def print_usage(result):
    if not "usage" in result:
        return
    usage = result["usage"]
    if not "prompt_tokens" in usage or not "completion_tokens" in usage or not "total_tokens" in usage:
        return

    prompt_tokens = usage["prompt_tokens"]
    completion_tokens = usage["completion_tokens"]
    total_tokens = usage["total_tokens"]
    print(f"tokens used: {prompt_tokens} prompt, {completion_tokens} completion, {total_tokens} total")

    if not "cost_USD" in result:
        return
    cost_USD = result["cost_USD"]
    if cost_USD > 0:
        print(f"estimated cost (USD): ${cost_USD:.2f}")

def combine_results(result1, model1, result2, model2, result3, model3):
    cost1 = compute_cost(result1["usage1"], model1)
    cost2 = compute_cost(result2["usage2"], model2)
    cost3 = compute_cost(result3["usage3"], model3)
    result = {
        "generated_json1": result1["generated_json1"],
        "elapsed_sec1": result1["elapsed_sec1"],
        "usage1": result1["usage1"],
        "cost_USD1": cost1,

        "generated_json2": result2["generated_json2"],
        "elapsed_sec2": result2["elapsed_sec2"],
        "usage2": result2["usage2"],
        "cost_USD2": cost2,

        "elapsed_sec3": result3["elapsed_sec3"],
        "usage3": result3["usage3"],
        "cost_USD3": cost3,

        "ok": result3["ok3"],
        "generated_json": result3["generated_json3"],
        "elapsed_sec": result1["elapsed_sec1"] + result2["elapsed_sec2"] + result3["elapsed_sec3"],
        "cost_USD": cost1 + cost2 + cost3
    }
    return result

#

def get_raw_training_doc():
    try:
        import requests
    except:
        print("The 'requests' module is not available. Try running this script with Blender:")
        print("$ blender --background --python gen.py -- <arguments>")
        return { f"ok": False, "error": "Python module 'requests' not found", "code": 0 }

    url = "https://raw.githubusercontent.com/connectome-neuprint/neuVid/master/documentation/training.md"
    headers = {
        "User-Agent": "request"
    }

    try:
        response = requests.get(url=url, headers=headers)
        response.raise_for_status()
    except requests.exceptions.ConnectionError as err:
        return { "ok": False, "error": str(err) }
    except requests.exceptions.HTTPError as err:
        return { "ok": False, "error": str(err) }
    
    text = response.text
    vers = get_version(text)
    return { "ok": True, "text": text, "source": url, "version": vers }

'''
# Local
def get_raw_training_doc():
    path = os.path.join(os.path.dirname(os.path.realpath(__file__)), "../documentation/training.md")
    path = os.path.realpath(path)
    try:
        with open(path, "r") as f:
            text = f.read()
            vers = get_version(text)
            print(f"Training {vers}")
            return { "ok": True, "text": text, "source": path, "version": vers }
    except:
        return { "ok": False, "error": f"cannot open '{path}'" }
'''

def generate(raw_doc, previous_result, user_request, api_key, models, temperature):
    model1 = models[0]
    doc1 = filter_doc(raw_doc, "1")

    # Step 1 has only the doc for creating groups of neurons, ROIs, etc.
    # Yet it tends to hallucinate commands for the animation section,
    # which directives in the prompt seem incapable of stopping.
    # So copy the good animation from the previous result now, and then
    # paste it over the bad animation from step 1, below.
    lines_copied = copy_animation(previous_result)

    prompt1 = get_prompt(doc1, previous_result, user_request, "1")
    result1 = submit_prompt(prompt1, api_key, model1, temperature, "1")
    if not result1["ok1"]:
        return { "ok": False, "error": result1["error"] }

    model2 = models[1]
    doc2 = filter_doc(raw_doc, "2")
    previous_result2 = result1["generated_json1"]

    # After pasting over the bad animation from step 1, store it back into
    # the results object, to be accessible in `combine_results`.
    previous_result2 = paste_animation(previous_result2, lines_copied)
    result1["generated_json1"] = previous_result2

    prompt2 = get_prompt(doc2, previous_result2, user_request, "2")
    result2 = submit_prompt(prompt2, api_key, model2, temperature, "2")
    if not result2["ok2"]:
        return { "ok": False, "error": result2["error"] }

    model3 = models[2]
    doc3 = filter_doc(raw_doc, "3")
    previous_result3 = result2["generated_json2"]

    # The user request is not needed for pass 3, which just applies fixes
    # like orientation correction.
    prompt3 = get_prompt(doc3, previous_result3, "", "3")
    result3 = submit_prompt(prompt3, api_key, model3, temperature, "3")
    if not result3["ok3"]:
        return { "ok": False, "error": result3["error"] }

    result = combine_results(result1, model1, result2, model2, result3, model3)
    return result

# This approach requires a powerful model with a big context, and even it that case
# it generally does not work as well as the three-step approach.
def generate_single_step(raw_doc, previous_result, user_request, api_key, models, temperature):
    model = models[0]
    doc = filter_doc(raw_doc, "SINGLE")

    prompt = get_prompt(doc, previous_result, user_request, "1")
    result = submit_prompt(prompt, api_key, model, temperature, "")
    if not result["ok"]:
        return { "ok": False, "error": result["error"] }

    cost = compute_cost(result["usage"], model)
    result["cost_USD"] = cost

    return result

#

if __name__ == "__main__":
    report_version()
    
    argv = sys.argv
    if "--" in argv:
        # Running as `blender --background --python <script> -- <more arguments>`
        argv = argv[argv.index("--") + 1:]
    else:
        # Running as `python <script> <more arguments>`
        argv = argv[1:]

    parser = argparse.ArgumentParser()
    parser.add_argument("request", help="natural language request for what to put in the video")
    parser.set_defaults(input="")
    parser.add_argument("--input", "-i", help="path to a JSON file to add to the prompt")
    # By default, print output.
    parser.set_defaults(output="")
    parser.add_argument("--output", "-o", help="path to the output JSON file")
    # "gpt-3.5-turbo-16k" is cheaper but does not work as well.
    parser.set_defaults(model="gpt-4")
    parser.add_argument("--model", "-m", help="OpenAI model name")
    parser.set_defaults(api_key="")
    parser.add_argument("--apikey", "-a", help="OpenAI API key")
    parser.set_defaults(temperature=0)
    parser.add_argument("--temperature", "-t", type=float, help="OpenAI model temperature")
    parser.set_defaults(single_step=False)
    parser.add_argument("--single", dest="single_step", action="store_true", help="use a single step (requires a big context)")
    parser.set_defaults(quiet=False)
    parser.add_argument("--quiet", "-q", action="store_true", help="run quietly, without printing usage statistics")
    args = parser.parse_args(argv)

    api_key = args.api_key 
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")

    raw_doc_data = get_raw_training_doc()
    if not raw_doc_data["ok"]:
        print(raw_doc_data["error"])
        sys.exit()
    if raw_doc_data["version"]:
        print(f"Training documentation version {raw_doc_data['version']}")

    models = [args.model, args.model, args.model]
    if args.single_step:
        result = generate(raw_doc_data["text"], args.input, args.request, api_key, models, args.temperature)
    else:
        result = generate_single_step(raw_doc_data["text"], args.input, args.request, api_key, models, args.temperature)

    if not result["ok"]:
        print(result["error"])
        sys.exit()

    if not args.quiet:
        elapsed_sec = result["elapsed_sec"]
        print(f"elapsed time: {elapsed_sec} seconds")
        print_usage(result)
    
    if args.output == "":
        print(result["generated_json"])
    else:
        with open(args.output, "w") as f:
            f.write(result["generated_json"])
