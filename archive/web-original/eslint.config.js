module.exports = [
    {
        files: ["*.js", "**/*.js"],
        languageOptions: {
            ecmaVersion: 2022,
            sourceType: "script",
            globals: {
                // Browser globals
                window: "readonly",
                document: "readonly",
                console: "readonly",
                fetch: "readonly",
                // Other common globals
                setTimeout: "readonly",
                clearTimeout: "readonly",
                setInterval: "readonly",
                clearInterval: "readonly"
            }
        },
        rules: {
            // Possible Errors
            "no-console": "off",
            "no-debugger": "error",
            "no-duplicate-case": "error",
            "no-empty": "error",
            "no-extra-semi": "error",
            "no-unreachable": "error",
            "valid-typeof": "error",
            
            // Best Practices
            "curly": "error",
            "eqeqeq": "error",
            "no-eval": "error",
            "no-implied-eval": "error",
            "no-var": "error",
            "prefer-const": "error",
            
            // Style
            "indent": ["error", 4],
            "quotes": ["error", "single"],
            "semi": ["error", "always"],
            "comma-dangle": ["error", "never"],
            "brace-style": ["error", "1tbs"],
            "space-before-blocks": "error",
            "keyword-spacing": "error"
        }
    }
];