# Introduction

I'd like to thank you for looking to contribute to this project, as this is part of an active development.

While these guidelines arent the law, following them will lead to easier merges due to less conflict between the ideology, security, and overall code flow.

This project is in active development by the Northern Arizona University Capstone team [BlueBox](https://ceias.nau.edu/capstone/projects/CS/2021/Bluebox-F20/). If you find an issue, please create a Github Issue. If it is a security vulnerability, please email them privately to one of the team members. 

We are not looking for feature improvements or bug fixes from outside the team at this time.
# Ground Rules
This section will lay out how to make changes and improvements to code, as well as general styling guidelines.

## How to Contribute
When contributing, this general flow which will be followed:
* Fork code
* Make changes in forked code
* Commit and push code to forked repository
* merge original code (If changes to master has been made on master which fork doesn't have)
* Submit a pull request

## Pull Requests
When creating a pull request, this is a general rule to follow on is expected, as well as formatting a pull request.

* Ensure Tests are still passing (When developed).
* Follow the general [code guidelines](##-code-guidelines).
* When attempting to make changes to master, the change should typically only be one feature.
If this is a bug fix, you can either include it with your feature, or merge it separately.
* Title of pull should be a short description of what has changed.
* Description should contain some info on specific changes (like file addition or function refactor), why it was changed, and what it does.
* Follow general code guidelines.
* If creating a new plugin or refactoring an old plugin, please follow the [plugin guidelines](##-plugin-guidelines).

## Code Guidelines
This will describe some of the expected operations and styling of code.

### Operation
Some general requirements for code operation:
* All configuration specific values should be stored in a configuration file, with defaults which work in a test environment
* These configuration specific values are typically data directories, server IP Addresses/ports, or potential security concerns
* If a new configuration file is required, it should be added to .gitignore

A lot of the different systems interact with each other, when making a change to one part of code, make sure that those changes will appear.
For example, if a change was made to a plugin and it now requires new arguments, this change will need to be reflected in the hubParse file, as this created the configurations.

### Styling
Some general styling and conventions are as follows:
* Add documentation (This will be added once the team decides how to document).
* Class/variable names are for what it is, function/method names are for what it is doing, and comments are for why it is doing it (or links to stack overflow articles)
* Code styling should typically follow that files similar styling, or a file like it. This isn't crucial, just strive for easily readable code.

## Plugin Guidelines
When adding or modifying a plugin these general guidelines should be followed. 
Here is a link to some information about plugins from the Jbrowse Wiki: [https://jbrowse.org/docs/faq.html#how-do-i-install-a-plugin](https://jbrowse.org/docs/faq.html#how-do-i-install-a-plugin)

### New Plugin
When a new plugin is created, first follow the new plugin guide for Jbrowse found here [https://jbrowse.org/docs/faq.html#how-do-i-create-a-plugin](https://jbrowse.org/docs/faq.html#how-do-i-create-a-plugin)
Then follow these guidelines
* Create repository for the new plugin
* Push the plugin to that repository

### Adding A New or Changed Plugin
For now, I'll have you message me, as the current system doesn't make it easy to submit pull requests with recursive submodule changes. This will change soon


