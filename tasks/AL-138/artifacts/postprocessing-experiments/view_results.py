#!/usr/bin/env python3
"""
View experiment results in HTML format.
"""

import html as html_module
import json
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Any, Dict


def generate_html(results_data: Dict[str, Any]) -> str:
    """Generate HTML page from results"""
    experiment_name = results_data.get("experiment", "Unknown Experiment")
    results = results_data.get("results", [])
    summary = results_data.get("summary", {})
    config = results_data.get("config", {})
    parse_field = config.get(
        "parse_field"
    )  # Can be None for transformation experiments
    parse_field_label = parse_field.capitalize() if parse_field else "Result"

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{experiment_name} - Results</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: #f5f5f5;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        h1 {{
            color: #333;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }}
        .summary {{
            background: #e8f5e9;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .summary h2 {{
            margin-top: 0;
            color: #2e7d32;
        }}
        .filters {{
            background: #fff3e0;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
        }}
        .filters select, .filters input {{
            margin: 5px;
            padding: 5px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        th, td {{
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }}
        th {{
            background-color: #4CAF50;
            color: white;
            position: sticky;
            top: 0;
        }}
        tr:nth-child(even) {{
            background-color: #f9f9f9;
        }}
        tr:hover {{
            background-color: #f5f5f5;
        }}
        .error {{
            color: red;
            font-weight: bold;
        }}
        .cached {{
            color: #666;
            font-style: italic;
        }}
        .response {{
            max-width: 500px;
            word-wrap: break-word;
            white-space: pre-wrap;
        }}
        .response-full {{
            max-width: 800px;
            word-wrap: break-word;
            white-space: pre-wrap;
            max-height: 300px;
            overflow-y: auto;
            background: #f9f9f9;
            padding: 10px;
            border-radius: 4px;
            font-size: 0.9em;
        }}
        .input-text {{
            max-width: 300px;
            word-wrap: break-word;
            white-space: pre-wrap;
            font-size: 0.9em;
            position: relative;
            cursor: help;
        }}
        .input-text-wrapper {{
            position: relative;
            display: inline-block;
        }}
        .input-tooltip {{
            visibility: hidden;
            position: absolute;
            background: #333;
            color: white;
            padding: 15px;
            border-radius: 4px;
            z-index: 1000;
            max-width: 600px;
            max-height: 500px;
            overflow-y: auto;
            word-wrap: break-word;
            white-space: pre-wrap;
            font-size: 0.85em;
            top: 100%;
            left: 0;
            margin-top: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
            line-height: 1.4;
            opacity: 0;
            transition: opacity 0.2s;
        }}
        .input-text-wrapper:hover .input-tooltip {{
            visibility: visible;
            opacity: 1;
        }}
        .comparison-table {{
            margin-top: 40px;
        }}
        .comparison-table th {{
            background-color: #2196F3;
        }}
        .comparison-cell {{
            text-align: center;
            cursor: pointer;
            position: relative;
        }}
        .comparison-cell:hover {{
            background-color: #e3f2fd;
        }}
        .tooltip {{
            position: absolute;
            background: #333;
            color: white;
            padding: 10px;
            border-radius: 4px;
            z-index: 1000;
            max-width: 500px;
            max-height: 400px;
            overflow-y: auto;
            word-wrap: break-word;
            white-space: pre-wrap;
            font-size: 0.85em;
            display: none;
            top: 100%;
            left: 0;
            margin-top: 5px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }}
        .comparison-cell {{
            position: relative;
        }}
        .comparison-cell:hover .tooltip {{
            display: block;
        }}
        .view-toggle {{
            margin: 20px 0;
        }}
        .view-toggle button {{
            padding: 10px 20px;
            margin-right: 10px;
            cursor: pointer;
            border: none;
            background: #4CAF50;
            color: white;
            border-radius: 4px;
        }}
        .view-toggle button.active {{
            background: #2e7d32;
        }}
        .view-section {{
            display: none;
        }}
        .view-section.active {{
            display: block;
        }}
        .disagreements {{
            background: #ffebee;
            padding: 15px;
            border-radius: 5px;
            margin: 20px 0;
            border-left: 4px solid #f44336;
            display: none;
        }}
        .disagreements.visible {{
            display: block;
        }}
        .toggle-disagreements {{
            background: #f44336;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            font-size: 14px;
            margin: 10px 0;
        }}
        .toggle-disagreements:hover {{
            background: #d32f2f;
        }}
        .disagreements h2 {{
            margin-top: 0;
            color: #c62828;
        }}
        .disagreement-item {{
            background: white;
            padding: 10px;
            margin: 10px 0;
            border-radius: 4px;
            border: 1px solid #ffcdd2;
        }}
        .disagreement-item strong {{
            color: #c62828;
        }}
        .model-result {{
            display: inline-block;
            margin: 5px 10px 5px 0;
            padding: 4px 8px;
            background: #f5f5f5;
            border-radius: 3px;
            font-size: 0.9em;
        }}
        .agreement {{
            background: #e8f5e9;
            border-left: 4px solid #4CAF50;
        }}
        .agreement h2 {{
            color: #2e7d32;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{experiment_name}</h1>
        
        <div class="summary">
            <h2>Summary</h2>
            <p><strong>Total tests:</strong> {summary.get("total_tests", 0)}</p>
            <p><strong>Successful:</strong> {summary.get("successful_tests", 0)}</p>
            <p><strong>Errors:</strong> {summary.get("error_tests", 0)}</p>
            <p><strong>Average latency:</strong> {summary.get("avg_latency", 0):.2f}s</p>
            <p><strong>Total cost:</strong> ${summary.get("total_cost", 0):.6f}</p>
        </div>
"""

    # Analyze model disagreements
    from collections import defaultdict

    by_input = defaultdict(list)

    for result in results:
        input_path = result.get("input_path", "").split("/")[-1]
        prompt_path = result.get("prompt_path", "").split("/")[-1]
        model = result.get("model", "").split("/")[-1]
        parsed = result.get("parsed_value") or "None"
        key = f"{input_path}|{prompt_path}"

        by_input[key].append(
            {
                "model": model,
                "parsed": parsed,
                "input_path": input_path,
                "prompt": prompt_path,
            }
        )

    # Find disagreements
    disagreements_list = []
    agreements_count = 0

    for key, model_results in sorted(by_input.items()):
        parsed_values = [r["parsed"] for r in model_results if r["parsed"] != "None"]
        unique_values = set(parsed_values)

        if len(unique_values) > 1:
            disagreements_list.append(
                {
                    "input": model_results[0]["input_path"],
                    "prompt": model_results[0]["prompt"],
                    "results": model_results,
                    "values": sorted(unique_values),
                }
            )
        elif len(unique_values) == 1:
            agreements_count += 1

    total_inputs = len(by_input)
    disagreements_count = len(disagreements_list)
    agreement_percentage = (
        (agreements_count / total_inputs * 100) if total_inputs > 0 else 0
    )

    # Generate disagreements section
    if disagreements_count > 0:
        html += f"""
        <button class="toggle-disagreements" onclick="toggleDisagreements()">
            ⚠️ Show Model Disagreements ({disagreements_count} of {total_inputs} inputs, {agreement_percentage:.1f}% agreement)
        </button>
        <div class="disagreements" id="disagreementsSection">
            <h2>⚠️ Model Disagreements ({disagreements_count} of {total_inputs} inputs)</h2>
            <p><strong>Agreement rate:</strong> {agreement_percentage:.1f}% ({agreements_count}/{total_inputs})</p>
"""
        for item in disagreements_list:
            html += f"""
            <div class="disagreement-item">
                <strong>{html_module.escape(item["input"])}</strong> ({html_module.escape(item["prompt"])})<br>
                <span style="color: #666;">Disagreement: {", ".join(item["values"])}</span><br>
"""
            for r in item["results"]:
                color_map = {
                    "safe": "#4CAF50",
                    "questionable": "#FF9800",
                    "nude": "#F44336",
                    "explicit": "#9C27B0",
                }
                color = color_map.get(r["parsed"].lower(), "#333")
                html += f'                <span class="model-result"><strong>{html_module.escape(r["model"])}</strong>: <span style="color: {color}; font-weight: bold;">{html_module.escape(r["parsed"])}</span></span>\n'
            html += "            </div>\n"

        html += "        </div>\n"
    else:
        html += f"""
        <div class="agreement">
            <h2>✅ Perfect Agreement!</h2>
            <p>All {total_inputs} inputs have consistent results across all models.</p>
        </div>
"""

    html += """
        
        <div class="filters">
            <h3>Filters</h3>
            <label>Model: <select id="modelFilter" onchange="filterTable()">
                <option value="">All</option>
            </select></label>
            <label>Prompt: <select id="promptFilter" onchange="filterTable()">
                <option value="">All</option>
            </select></label>
            <label>Input Type: <select id="typeFilter" onchange="filterTable()">
                <option value="">All</option>
                <option value="dialog">Dialog</option>
                <option value="message">Message</option>
            </select></label>
            <label>Show Errors Only: <input type="checkbox" id="errorFilter" onchange="filterTable()"></label>
            <label>{parse_field_label}: <select id="categoryFilter" onchange="filterTable()">
                <option value="">All</option>
            </select></label>
        </div>
        
        <div class="view-toggle">
            <button onclick="showView('detailed')" id="btnDetailed" class="active">Detailed View</button>
            <button onclick="showView('comparison')" id="btnComparison">Comparison Matrix</button>
            <button onclick="showView('byInput')" id="btnByInput">By Input</button>
        </div>
        
        <div id="detailedView" class="view-section active">
        <table id="resultsTable">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Prompt</th>
                    <th>Input Type</th>
                    <th>Input</th>
                    <th>{parse_field_label}</th>
                    <th>Response</th>
                    <th>Latency</th>
                    <th>Cost</th>
                    <th>Status</th>
                </tr>
            </thead>
            <tbody>
"""

    # Generate table rows
    for result in results:
        model = result.get("model", "").split("/")[-1]
        prompt = result.get("prompt_path", "").split("/")[-1]
        input_type = result.get("input_type", "")
        input_path = result.get("input_path", "").split("/")[-1]
        input_full = result.get("input", "")  # Full text for tooltip
        input_preview = result.get(
            "input_preview", input_full
        )  # Short preview for table
        input_text = (
            input_preview[:100] + "..." if len(input_preview) > 100 else input_preview
        )
        parsed_value = result.get("parsed_value", "")
        response = result.get("response", "")
        latency = result.get("latency", 0)
        cost = result.get("cost", 0)
        error = result.get("error")

        # Format parsed value (dynamic based on parse_field)
        parsed_html = ""
        if parsed_value:
            # For known categories, use color coding
            colors = {
                "safe": "#4CAF50",
                "questionable": "#FF9800",
                "nude": "#F44336",
                "explicit": "#9C27B0",
            }
            color = colors.get(parsed_value.lower(), "#333")
            parsed_html = f'<span style="color: {color}; font-weight: bold;">{parsed_value}</span>'
        elif error:
            parsed_html = '<span style="color: red;">ERROR</span>'
        else:
            parsed_html = '<span style="color: #999;">-</span>'

        status = f'<span class="error">ERROR: {error}</span>' if error else "✅ OK"

        html += f"""
                <tr data-model="{model}" data-prompt="{prompt}" data-type="{input_type}" data-error="{bool(error)}" data-category="{parsed_value or ""}">
                    <td>{model}</td>
                    <td>{prompt}</td>
                    <td>{input_type}</td>
                    <td>
                        <div class="input-text-wrapper">
                            <div class="input-text" title="{html_module.escape(input_path)}">
                                {html_module.escape(input_text)}
                            </div>
                            <div class="input-tooltip">
                                <strong>{html_module.escape(input_path)}</strong><br><br>
                                {html_module.escape(input_full)}
                            </div>
                        </div>
                    </td>
                    <td>{parsed_html}</td>
                    <td class="response-full" title="Full response">{html_module.escape(response)}</td>
                    <td>{latency:.2f}s</td>
                    <td>${cost:.6f}</td>
                    <td>{status}</td>
                </tr>
"""

    html += """
            </tbody>
        </table>
        </div>
        
        <div id="comparisonView" class="view-section">
        <table id="comparisonTable" class="comparison-table">
            <thead>
                <tr>
                    <th>Input</th>
"""

    # Build comparison matrix: rows = inputs, columns = models
    # Group results by input_path and prompt_path (assuming same prompt for comparison)
    input_groups = {}
    models_set = set()

    for result in results:
        input_path = result.get("input_path", "").split("/")[-1]
        prompt_path = result.get("prompt_path", "").split("/")[-1]
        model = result.get("model", "").split("/")[-1]
        key = f"{input_path}|{prompt_path}"

        if key not in input_groups:
            input_full = result.get("input", "")
            input_groups[key] = {
                "input_path": input_path,
                "input_type": result.get("input_type", ""),
                "input_full": input_full,  # Full text for tooltip
                "input_text": input_full[:150] + "..."
                if len(input_full) > 150
                else input_full,
                "prompt": prompt_path,
                "models": {},
            }

        input_groups[key]["models"][model] = result
        models_set.add(model)

    # Generate header with models
    models_sorted = sorted(models_set)
    for model in models_sorted:
        html += f"                    <th>{model}</th>\n"

    html += """                </tr>
            </thead>
            <tbody>
"""

    # Generate rows
    for key, group in sorted(input_groups.items()):
        input_path = group["input_path"]
        input_type = group["input_type"]
        input_text = group["input_text"]
        input_full = group.get("input_full", input_text)
        prompt = group["prompt"]

        html += f"""
                <tr>
                    <td>
                        <div class="input-text-wrapper">
                            <strong>{html_module.escape(input_path)}</strong><br>
                            <small style="color: #666;">{html_module.escape(input_type)} | {html_module.escape(prompt)}</small><br>
                            <div class="input-text" style="margin-top: 5px;">{html_module.escape(input_text)}</div>
                            <div class="input-tooltip">
                                <strong>{html_module.escape(input_path)}</strong><br>
                                <small style="color: #ccc;">{html_module.escape(input_type)} | {html_module.escape(prompt)}</small><br><br>
                                {html_module.escape(input_full)}
                            </div>
                        </div>
                    </td>
"""

        for model in models_sorted:
            result = group["models"].get(model, {})
            parsed_value = result.get("parsed_value", "")
            response = result.get("response", "")
            error = result.get("error")
            latency = result.get("latency", 0)

            if error:
                cell_content = (
                    '<span style="color: red; font-weight: bold;">ERROR</span>'
                )
                tooltip_text = f"Error: {html_module.escape(str(error))}"
            elif parsed_value:
                colors = {
                    "safe": "#4CAF50",
                    "questionable": "#FF9800",
                    "nude": "#F44336",
                    "explicit": "#9C27B0",
                }
                color = colors.get(parsed_value.lower(), "#333")
                cell_content = f'<span style="color: {color}; font-weight: bold;">{html_module.escape(parsed_value)}</span>'
                tooltip_text = f"Response: {html_module.escape(response[:500])}{'...' if len(response) > 500 else ''}<br>Latency: {latency:.2f}s"
            else:
                cell_content = '<span style="color: #999;">-</span>'
                tooltip_text = "No result"

            html += f"""
                    <td class="comparison-cell">
                        {cell_content}
                        <div class="tooltip">{tooltip_text}</div>
                    </td>
"""

        html += "                </tr>\n"

    html += """            </tbody>
        </table>
        </div>
        
        <div id="byInputView" class="view-section">
        <table id="byInputTable" class="results-table">
            <thead>
                <tr>
                    <th>Model</th>
                    <th>Prompt</th>
                    <th>Input</th>
                    <th>Result</th>
                </tr>
            </thead>
            <tbody>
"""

    # Build "By Input" view: simple table with model / prompt / input / result
    # Sort by input, then by prompt, then by model
    sorted_results = sorted(
        results,
        key=lambda r: (
            r.get("input_path", "").split("/")[-1],
            r.get("prompt_path", "").split("/")[-1],
            r.get("model", "").split("/")[-1],
        ),
    )

    for result in sorted_results:
        model = result.get("model", "").split("/")[-1]
        prompt = result.get("prompt_path", "").split("/")[-1]
        input_path = result.get("input_path", "").split("/")[-1]
        input_type = result.get("input_type", "")
        input_full = result.get("input", "")
        input_text = input_full[:150] + "..." if len(input_full) > 150 else input_full
        response = result.get("response", "")
        parsed_value = result.get("parsed_value", "")
        error = result.get("error")

        # Show parsed_value if available (e.g., from <result> tag), otherwise show full response
        if error:
            result_content = f'<span style="color: red;">ERROR: {html_module.escape(str(error))}</span>'
        elif parsed_value:
            # Show parsed value (e.g., extracted from <result> tag)
            result_content = f'<div class="response-full" title="Parsed result">{html_module.escape(parsed_value)}</div>'
        else:
            # Show full response if no parsing was done
            result_content = f'<div class="response-full" title="Full response">{html_module.escape(response)}</div>'

        # Determine category for filtering (if parse_field exists)
        category_value = parsed_value if parsed_value else "None"

        html += f"""
                <tr data-model="{html_module.escape(model)}" 
                    data-prompt="{html_module.escape(prompt)}" 
                    data-type="{html_module.escape(input_type)}" 
                    data-error="{"True" if error else "False"}" 
                    data-category="{html_module.escape(category_value)}">
                    <td>{html_module.escape(model)}</td>
                    <td>{html_module.escape(prompt)}</td>
                    <td>
                        <div class="input-text-wrapper">
                            <strong>{html_module.escape(input_path)}</strong><br>
                            <small style="color: #666;">{html_module.escape(input_type)}</small><br>
                            <div class="input-text" style="margin-top: 5px;">{html_module.escape(input_text)}</div>
                            <div class="input-tooltip">
                                <strong>{html_module.escape(input_path)}</strong><br>
                                <small style="color: #ccc;">{html_module.escape(input_type)}</small><br><br>
                                {html_module.escape(input_full)}
                            </div>
                        </div>
                    </td>
                    <td>{result_content}</td>
                </tr>
"""

    html += """            </tbody>
        </table>
        </div>
    </div>
    
    <script>
        // Populate filter options from both tables
        const table = document.getElementById('resultsTable');
        const byInputTable = document.getElementById('byInputTable');
        const models = new Set();
        const prompts = new Set();
        const categories = new Set();
        
        // Collect from detailed view
        if (table) {
            Array.from(table.querySelectorAll('tbody tr')).forEach(row => {
                models.add(row.dataset.model);
                prompts.add(row.dataset.prompt);
                if (row.dataset.category) {
                    categories.add(row.dataset.category);
                }
            });
        }
        
        // Collect from by input view
        if (byInputTable) {
            Array.from(byInputTable.querySelectorAll('tbody tr')).forEach(row => {
                models.add(row.dataset.model);
                prompts.add(row.dataset.prompt);
                if (row.dataset.category) {
                    categories.add(row.dataset.category);
                }
            });
        }
        
        const modelFilter = document.getElementById('modelFilter');
        Array.from(models).sort().forEach(model => {
            const option = document.createElement('option');
            option.value = model;
            option.textContent = model;
            modelFilter.appendChild(option);
        });
        
        const promptFilter = document.getElementById('promptFilter');
        Array.from(prompts).sort().forEach(prompt => {
            const option = document.createElement('option');
            option.value = prompt;
            option.textContent = prompt;
            promptFilter.appendChild(option);
        });
        
        const categoryFilter = document.getElementById('categoryFilter');
        Array.from(categories).sort().forEach(category => {
            const option = document.createElement('option');
            option.value = category;
            option.textContent = category.charAt(0).toUpperCase() + category.slice(1);
            categoryFilter.appendChild(option);
        });
        
        function filterTable() {
            const modelFilter = document.getElementById('modelFilter').value;
            const promptFilter = document.getElementById('promptFilter').value;
            const typeFilter = document.getElementById('typeFilter').value;
            const errorFilter = document.getElementById('errorFilter').checked;
            const categoryFilter = document.getElementById('categoryFilter').value;
            
            // Filter detailed view table
            const table = document.getElementById('resultsTable');
            if (table) {
                Array.from(table.querySelectorAll('tbody tr')).forEach(row => {
                    const matchModel = !modelFilter || row.dataset.model === modelFilter;
                    const matchPrompt = !promptFilter || row.dataset.prompt === promptFilter;
                    const matchType = !typeFilter || row.dataset.type === typeFilter;
                    const matchError = !errorFilter || row.dataset.error === 'True';
                    const matchCategory = !categoryFilter || row.dataset.category === categoryFilter;
                    
                    row.style.display = (matchModel && matchPrompt && matchType && matchError && matchCategory) ? '' : 'none';
                });
            }
            
            // Filter by input view table
            const byInputTable = document.getElementById('byInputTable');
            if (byInputTable) {
                Array.from(byInputTable.querySelectorAll('tbody tr')).forEach(row => {
                    const matchModel = !modelFilter || row.dataset.model === modelFilter;
                    const matchPrompt = !promptFilter || row.dataset.prompt === promptFilter;
                    const matchType = !typeFilter || row.dataset.type === typeFilter;
                    const matchError = !errorFilter || row.dataset.error === 'True';
                    const matchCategory = !categoryFilter || row.dataset.category === categoryFilter;
                    
                    row.style.display = (matchModel && matchPrompt && matchType && matchError && matchCategory) ? '' : 'none';
                });
            }
        }
        
        function toggleDisagreements() {
            const section = document.getElementById('disagreementsSection');
            const button = document.querySelector('.toggle-disagreements');
            if (section && button) {
                if (section.classList.contains('visible')) {
                    section.classList.remove('visible');
                    button.textContent = button.textContent.replace('Hide', 'Show');
                } else {
                    section.classList.add('visible');
                    button.textContent = button.textContent.replace('Show', 'Hide');
                }
            }
        }
        
        function showView(viewName) {
            // Hide all views
            document.getElementById('detailedView').classList.remove('active');
            document.getElementById('comparisonView').classList.remove('active');
            document.getElementById('byInputView').classList.remove('active');
            document.getElementById('btnDetailed').classList.remove('active');
            document.getElementById('btnComparison').classList.remove('active');
            document.getElementById('btnByInput').classList.remove('active');
            
            // Show selected view
            if (viewName === 'detailed') {
                document.getElementById('detailedView').classList.add('active');
                document.getElementById('btnDetailed').classList.add('active');
            } else if (viewName === 'comparison') {
                document.getElementById('comparisonView').classList.add('active');
                document.getElementById('btnComparison').classList.add('active');
            } else if (viewName === 'byInput') {
                document.getElementById('byInputView').classList.add('active');
                document.getElementById('btnByInput').classList.add('active');
            }
        }
    </script>
</body>
</html>
"""

    return html


def main():
    base_dir = Path(__file__).parent

    # If argument provided, use it
    if len(sys.argv) > 1:
        results_file = Path(sys.argv[1])
        if not results_file.is_absolute():
            # Check if path contains experiment class folder (e.g., "context_detection/results/exp.json")
            if "/" in str(results_file) or "\\" in str(results_file):
                # Path contains subdirectory, resolve relative to base_dir
                results_file = base_dir / results_file
            else:
                # Just filename, try to find in any experiment class folder
                # First try old structure
                old_results_dir = base_dir / "results"
                if (old_results_dir / results_file).exists():
                    results_file = old_results_dir / results_file
                else:
                    # Search in all experiment class folders
                    found = False
                    for exp_dir in base_dir.iterdir():
                        if (
                            exp_dir.is_dir()
                            and (exp_dir / "results" / results_file).exists()
                        ):
                            results_file = exp_dir / "results" / results_file
                            found = True
                            break
                    if not found:
                        results_file = (
                            old_results_dir / results_file
                        )  # Will fail with error below
    else:
        # List all JSON files in all results directories
        json_files = []

        # Check old structure first
        old_results_dir = base_dir / "results"
        if old_results_dir.exists():
            json_files.extend(
                sorted(old_results_dir.glob("*_results.json"), key=lambda f: f.name)
            )

        # Check all experiment class folders
        for exp_dir in base_dir.iterdir():
            if exp_dir.is_dir() and (exp_dir / "results").exists():
                class_files = sorted(
                    (exp_dir / "results").glob("*_results.json"), key=lambda f: f.name
                )
                json_files.extend(class_files)

        # Remove duplicates and sort
        json_files = sorted(set(json_files), key=lambda f: f.name)

        if not json_files:
            print("No result files found in any results/ directory")
            return

        print("Available result files:")
        for i, f in enumerate(json_files, 1):
            # Show relative path from base_dir
            rel_path = f.relative_to(base_dir)
            print(f"{i}. {rel_path}")

        choice = input(
            "\nEnter number to view (or press Enter to view first): "
        ).strip()

        if choice:
            try:
                idx = int(choice) - 1
                results_file = json_files[idx]
            except (ValueError, IndexError):
                print("Invalid choice, using first file")
                results_file = json_files[0]
        else:
            results_file = json_files[0]

    if not results_file.exists():
        print(f"Error: Results file not found: {results_file}")
        return

    # Load results
    with open(results_file, "r") as f:
        results_data = json.load(f)

    # Generate HTML
    html = generate_html(results_data)

    # Save to temp file and open
    with tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False) as f:
        f.write(html)
        temp_path = f.name

    print(f"Opening results in browser: {temp_path}")
    webbrowser.open(f"file://{temp_path}")


if __name__ == "__main__":
    main()
