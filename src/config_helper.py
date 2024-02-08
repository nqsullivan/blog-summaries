# This file is used to read from the config file and return the values of the parameters

import configparser
import os


def get_config():
    config = configparser.ConfigParser()

    if not os.path.exists('config.ini'):
        print("Could not find config.ini")
        print("Please create a config.ini file")
        exit(1)

    config.read('config.ini')

    return config


def get_config_value(section, key):
    config = get_config()

    if config[section][key] is None:
        print(f"Could not find {key} in the config file")
        print(f"Please add {key} to the config file")
        exit(1)

    return config[section][key]


def get_config_value_env(section, key):
    config = get_config()

    print(section, key)
    print(config[section][key])

    if os.environ.get(config[section][key]) is None:
        print(f"Could not find {key} in environment variables")
        print(f"Please set {key} in the environment variables")
        exit(1)

    return os.environ.get(config[section][key])


keys_to_prompt_for = {
    'GOOGLE': ['BLOG_SUMMARIES_GOOGLE_CREDENTIALS'],
    'OPENAI': ['BLOG_SUMMARIES_OPENAI_API_KEY']
}

if __name__ == '__main__':
    # This will be a simple cli to prompt the user for the config values
    print("Welcome to the config helper!")
    print("This will prompt you for the values for information that will be stored in the environment")

    for s, k in keys_to_prompt_for.items():
        print(f"Configuring {s}...")
        for key in k:
            value = input(f"Enter value for {key}: ")
            os.environ[key] = value

            if os.path.exists(os.path.expanduser('~/.bashrc')):
                # Write at the beginning of the file
                with open(os.path.expanduser('~/.bashrc'), 'r') as f:
                    content = f.read()

                with open(os.path.expanduser('~/.bashrc'), 'w') as f:
                    f.write(f"export {key}={value}\n{content}")

            if os.path.exists(os.path.expanduser('~/.zshrc')):
                # Write at the beginning of the file
                with open(os.path.expanduser('~/.zshrc'), 'r') as f:
                    content = f.read()

                with open(os.path.expanduser('~/.zshrc'), 'w') as f:
                    f.write(f"export {key}={value}\n{content}")

            print(f"Set {key} to {value}")
        print(f"Finished configuring {s}")
