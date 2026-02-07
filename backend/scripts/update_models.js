// MongoDB update script for LAYRA model configuration
db = db.getSiblingDB('chat_mongodb');

print("📋 Current configuration:");
var current = db.model_config.findOne({username: 'thesis'});
if (current) {
    print("  User: " + current.username);
    print("  Current models: " + current.models.length);
    current.models.forEach(function(model) {
        print("    - " + model.model_name + " (ID: " + model.model_id + ")");
    });
    print("  Selected model: " + current.selected_model);
}

// New model configurations
var newModels = [
    {
        model_id: 'thesis_deepseek_v3_2_3_user',
        model_name: 'deepseek-v3.2',
        model_url: null,
        api_key: null,
        base_used: [
            {
                name: 'Thesis Corpus',
                baseId: 'thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1'
            }
        ],
        system_prompt: 'All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).',
        temperature: -1,
        max_length: -1,
        top_P: -1,
        top_K: -1,
        score_threshold: 10
    },
    {
        model_id: 'thesis_deepseek_r1_4_user',
        model_name: 'deepseek-r1',
        model_url: null,
        api_key: null,
        base_used: [
            {
                name: 'Thesis Corpus',
                baseId: 'thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1'
            }
        ],
        system_prompt: 'All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).',
        temperature: -1,
        max_length: -1,
        top_P: -1,
        top_K: -1,
        score_threshold: 10
    },
    {
        model_id: 'thesis_kimi_k2_thinking_5_user',
        model_name: 'kimi-k2-thinking',
        model_url: null,
        api_key: null,
        base_used: [
            {
                name: 'Thesis Corpus',
                baseId: 'thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1'
            }
        ],
        system_prompt: 'All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).',
        temperature: -1,
        max_length: -1,
        top_P: -1,
        top_K: -1,
        score_threshold: 10
    },
    {
        model_id: 'thesis_glm_4_7_6_user',
        model_name: 'glm-4.7',
        model_url: null,
        api_key: null,
        base_used: [
            {
                name: 'Thesis Corpus',
                baseId: 'thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1'
            }
        ],
        system_prompt: 'All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).',
        temperature: -1,
        max_length: -1,
        top_P: -1,
        top_K: -1,
        score_threshold: 10
    },
    {
        model_id: 'thesis_glm_4_7_flash_7_user',
        model_name: 'glm-4.7',
        model_url: null,
        api_key: null,
        base_used: [
            {
                name: 'Thesis Corpus',
                baseId: 'thesis_fbd5d3a6-3911-4be0-a4b3-864ec91bc3c1'
            }
        ],
        system_prompt: 'All outputs in Markdown format, especially mathematical formulas in Latex format($formula$).',
        temperature: -1,
        max_length: -1,
        top_P: -1,
        top_K: -1,
        score_threshold: 10
    }
];

print("\n✨ New configuration:");
newModels.forEach(function(model) {
    print("  - " + model.model_name + " (ID: " + model.model_id + ")");
});

print("\n🔄 Updating database...");
var result = db.model_config.updateOne(
    {username: 'thesis'},
    {
        $set: {
            models: newModels,
            selected_model: 'thesis_glm_4_7_6_user',
            updated_at: new Date().toISOString()
        }
    }
);

print("✅ Update result:");
print("  Matched: " + result.matchedCount + " document(s)");
print("  Modified: " + result.modifiedCount + " document(s)");

print("\n🔍 Verification:");
var updated = db.model_config.findOne({username: 'thesis'});
if (updated) {
    print("  Total models: " + updated.models.length);
    print("  Selected model: " + updated.selected_model);
    
    var modelNames = updated.models.map(function(m) { return m.model_name; });
    print("  Available models: " + modelNames.join(', '));
    
    // Check for null values
    updated.models.forEach(function(model) {
        if (model.api_key !== null) {
            print("  ⚠️  Warning: " + model.model_name + " has API key in database (should be null)");
        }
        if (model.model_url !== null) {
            print("  ⚠️  Warning: " + model.model_name + " has model_url in database (should be null)");
        }
    });
}

print("\n✅ Update complete!");