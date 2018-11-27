import collections
import json
import os

from .base_component import ComponentRegistry

from .base_component import generate_class
from .base_component import generate_class_file
from .base_component import generate_export_string_r
from .base_component import generate_rpkg

from .base_component import write_class_file_r
from .base_component import write_help_file_r
from .base_component import write_js_metadata_r

def _get_metadata(metadata_path):
    # Start processing
    with open(metadata_path) as data_file:
        json_string = data_file.read()
        data = json\
            .JSONDecoder(object_pairs_hook=collections.OrderedDict)\
            .decode(json_string)
    return data


def load_components(metadata_path,
                    namespace='default_namespace'):
    """Load React component metadata into a format Dash can parse.

    Usage: load_components('../../component-suites/lib/metadata.json')

    Keyword arguments:
    metadata_path -- a path to a JSON file created by
    [`react-docgen`](https://github.com/reactjs/react-docgen).

    Returns:
    components -- a list of component objects with keys
    `type`, `valid_kwargs`, and `setup`.
    """

    # Register the component lib for index include.
    ComponentRegistry.registry.add(namespace)
    components = []

    data = _get_metadata(metadata_path)

    # Iterate over each property name (which is a path to the component)
    for componentPath in data:
        componentData = data[componentPath]

        # Extract component name from path
        # e.g. src/components/MyControl.react.js
        # TODO Make more robust - some folks will write .jsx and others
        # will be on windows. Unfortunately react-docgen doesn't include
        # the name of the component atm.
        name = componentPath.split('/').pop().split('.')[0]
        component = generate_class(
            name,
            componentData['props'],
            componentData['description'],
            namespace
        )

        components.append(component)

    return components


def generate_classes(namespace, metadata_path='lib/metadata.json'):
    """Load React component metadata into a format Dash can parse,
    then create python class files.

    Usage: generate_classes()

    Keyword arguments:
    namespace -- name of the generated python package (also output dir)

    metadata_path -- a path to a JSON file created by
    [`react-docgen`](https://github.com/reactjs/react-docgen).

    Returns:
    """

    data = _get_metadata(metadata_path)
    imports_path = os.path.join(namespace, '_imports_.py')

    # Make sure the file doesn't exist, as we use append write
    if os.path.exists(imports_path):
        os.remove(imports_path)

    # Iterate over each property name (which is a path to the component)
    for componentPath in data:
        componentData = data[componentPath]

        # Extract component name from path
        # e.g. src/components/MyControl.react.js
        # TODO Make more robust - some folks will write .jsx and others
        # will be on windows. Unfortunately react-docgen doesn't include
        # the name of the component atm.
        name = componentPath.split('/').pop().split('.')[0]
        generate_class_file(
            name,
            componentData['props'],
            componentData['description'],
            namespace
        )

        # Add an import statement for this component
        with open(imports_path, 'a') as f:
            f.write('from .{0:s} import {0:s}\n'.format(name))

    # Add the __all__ value so we can import * from _imports_
    all_imports = [p.split('/').pop().split('.')[0] for p in data]
    with open(imports_path, 'a') as f:
        array_string = '[\n'
        for a in all_imports:
            array_string += '    "{:s}",\n'.format(a)
        array_string += ']\n'
        f.write('\n\n__all__ = {:s}'.format(array_string))

def generate_classes_r(namespace, metadata_path='lib/metadata.json', pkgjson_path='package.json'):
    """Load React component metadata into a format Dash can parse,
    then create python class files.

    Usage: generate_classes_r()

    Keyword arguments:
    namespace -- name of the generated python package (also output dir)

    metadata_path -- a path to a JSON file created by
    [`react-docgen`](https://github.com/reactjs/react-docgen).

    pkgjson_path -- a path to a JSON file created by
    [`cookiecutter`](https://github.com/audreyr/cookiecutter).

    Returns:
    """

    data = _get_metadata(metadata_path)
    pkg_data = _get_metadata(pkgjson_path)
    imports_path = os.path.join(namespace, '_imports_.py')
    export_string = ''

    if namespace == 'dash_html_components':
        prefix = 'html'
    elif namespace == 'dash_core_components':
        prefix = 'core'
    else:
        prefix = ''

    # Remove the R NAMESPACE file if it exists, this will be repopulated
    if os.path.isfile('NAMESPACE'):
        os.remove('NAMESPACE')

    # Iterate over each property name (which is a path to the component)
    for componentPath in data:
        componentData = data[componentPath]

        # Extract component name from path
        # e.g. src/components/MyControl.react.js
        # TODO Make more robust - some folks will write .jsx and others
        # will be on windows. Unfortunately react-docgen doesn't include
        # the name of the component atm.
        name = componentPath.split('/').pop().split('.')[0]

        export_string += generate_export_string_r(name, prefix)

        # generate and write out R functions which will serve an analogous
        # purpose to the classes in Python which interface with the
        # Dash components
        write_class_file_r(
            name,
            componentData['props'],
            componentData['description'],
            namespace,
            prefix
        )

        # generate the internal (not exported to the user) functions which
        # supply the JavaScript dependencies to the htmlDependency package,
        # which is required by DashR (this avoids having to generate an
        # RData file from within Python, given the current package generation
        # workflow)
        write_js_metadata_r(
            namespace
        )

        # generate the R help pages for each of the Dash components that we
        # are transpiling -- this is done to avoid using Roxygen2 syntax,
        # we may eventually be able to generate similar documentation using
        # doxygen and an R plugin, but for now we'll just do it on our own
        # from within Python
        write_help_file_r(
            name,
            componentData['props'],
            prefix
        )

    # now, bundle up the package information and create all the requisite
    # elements of an R package, so that the end result is installable either
    # locally or directly from GitHub
    generate_rpkg(
        pkg_data,
        namespace,
        export_string
    )
