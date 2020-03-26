Alias Translations
######################################

.. currentmodule:: tk_framework_aliastranslations


Introduction
======================================

In order to convert a file to a different format, you need to use the :class:`Translator` class.


Sample Code: Translate a wire file to a CATPart file
----------------------------------------------------
Here is a simple piece of code to convert an Alias wire file to a CATPart file::

    source_path = "/path/to/file.wire"
    destination_path = "/path/to/file.CATPart"

    translator = Translator(source_path, destination_path)

    # If needed, we can add some extra attributes to the conversion
    # Here, for example, we want to use a specific version of CATPart
    # To find the list of all the available arguments, please refer to the command line options
    translator.add_extra_param("r", 19)

    translator.execute()



Translator
=====================================================

.. autoclass:: Translator
    :members:
