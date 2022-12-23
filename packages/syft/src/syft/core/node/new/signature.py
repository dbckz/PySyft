# stdlib
from inspect import Parameter
from inspect import Signature
from inspect import _ParameterKind

# relative
from ...common.serde import recursive_serde_register
from ...common.serde.deserialize import _deserialize
from ...common.serde.serialize import _serialize

recursive_serde_register(_ParameterKind)


recursive_serde_register(
    Parameter, attr_allowlist=["_annotation", "_name", "_kind", "_default"]
)


# def serialize_parameter(obj: Parameter) -> bytes:
#     # 🟡 TODO: Perhaps we can keep this as a type not a string
#     # currently types arent always being sent correctly maybe due to the path?
#     # instead we can send the fqn and recover it in the type checker on the client side
#     annotation = obj.annotation
#     if not isinstance(annotation, str):
#         annotation = f"{annotation.__module__}.{annotation.__name__}"
#     obj_dict = {
#         "name": obj.name,
#         "kind": obj.kind,
#         "default": obj.default,
#         "annotation": annotation,
#     }
#     return _serialize(obj_dict, to_bytes=True)


# def deserialize_parameter(blob: bytes) -> Parameter:
#     obj_dict = _deserialize(blob, from_bytes=True)
#     return Parameter(**obj_dict)


# recursive_serde_register(Parameter, serialize_parameter, deserialize_parameter)


def serialize_signature(obj: Signature) -> bytes:
    parameters = list(dict(obj.parameters).values())
    return_annotation = obj.return_annotation
    obj_dict = {"parameters": parameters, "return_annotation": return_annotation}
    return _serialize(obj_dict, to_bytes=True)


def deserialize_signature(blob: bytes) -> Signature:
    obj_dict = _deserialize(blob, from_bytes=True)
    return Signature(**obj_dict)


recursive_serde_register(Signature, serialize_signature, deserialize_signature)
