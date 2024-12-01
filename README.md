# Crypto Stream

## Setting up pre-commit

To set up the pre-commit hooks defined in your .pre-commit-config.yaml file, you'll need to follow these steps:

1. Install pre-commit: First, ensure that you have pre-commit installed. You can install it using pip:

   ```
   pip install pre-commit
   ```

2. Install the Hooks: Navigate to the root of your repository (where the `.pre-commit-config.yaml` file is located) and run the following command to install the hooks:

   ```
   pre-commit install
   ```

    This command sets up the pre-commit hooks to run automatically before each commit.


3. Run the Hooks Manually (Optional): If you want to run the hooks on all files in your repository immediately, you can use:

   ```
   pre-commit run --all-files
   ```

   Now, whenever you make a commit, the pre-commit hooks will automatically run. If any hook fails, the commit will be aborted, and you'll need to fix the issues before trying to commit again.

4. Updating Hooks: If you update the .pre-commit-config.yaml file or want to ensure you have the latest versions of the hooks, you can run:

   ```
   pre-commit autoupdate
   ```

    This command updates the hooks to their latest versions as specified in the configuration file.
