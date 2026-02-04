# AUTO GENERATED FILE - DO NOT EDIT

import typing  # noqa: F401
from typing_extensions import TypedDict, NotRequired, Literal # noqa: F401
from dash.development.base_component import Component, _explicitize_args

ComponentSingleType = typing.Union[str, int, float, Component, None]
ComponentType = typing.Union[
    ComponentSingleType,
    typing.Sequence[ComponentSingleType],
]

NumberType = typing.Union[
    typing.SupportsFloat, typing.SupportsInt, typing.SupportsComplex
]


class Editor(Component):
    """An Editor component.


Keyword arguments:

- id (string; optional)

- data (boolean | number | string | dict | list; optional)

- setProps (optional)

- value (boolean | number | string | dict | list; optional)"""
    _children_props: typing.List[str] = []
    _base_nodes = ['children']
    _namespace = 'dash_component_editor'
    _type = 'Editor'


    def __init__(
        self,
        id: typing.Optional[typing.Union[str, dict]] = None,
        data: typing.Optional[typing.Any] = None,
        value: typing.Optional[typing.Any] = None,
        **kwargs
    ):
        self._prop_names = ['id', 'data', 'setProps', 'value']
        self._valid_wildcard_attributes =            []
        self.available_properties = ['id', 'data', 'setProps', 'value']
        self.available_wildcard_properties =            []
        _explicit_args = kwargs.pop('_explicit_args')
        _locals = locals()
        _locals.update(kwargs)  # For wildcard attrs and excess named props
        args = {k: _locals[k] for k in _explicit_args}

        super(Editor, self).__init__(**args)

setattr(Editor, "__init__", _explicitize_args(Editor.__init__))
