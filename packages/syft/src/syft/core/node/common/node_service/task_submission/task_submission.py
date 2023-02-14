# stdlib
from datetime import date
from io import StringIO
import sys
from typing import Any
from typing import Dict
from typing import List
from typing import Optional
from typing import Type

# third party
from nacl.signing import VerifyKey
from typing_extensions import final

# relative
from ...... import logger
from ......core.common.uid import UID
from ......core.store.storeable_object import StorableObject
from .....common.group import VERIFYALL
from .....common.serde.serializable import serializable
from ....abstract.node import AbstractNode
from ....domain_interface import DomainInterface
from ....domain_msg_registry import DomainMessageRegistry
from ...node_table.task import NoSQLTask
from ...permissions.permissions import BasePermission
from ...permissions.user_permissions import NoRestriction
from ...permissions.user_permissions import UserIsOwner
from ..generic_payload.syft_message import NewSyftMessage as SyftMessage
from ..generic_payload.syft_message import ReplyPayload
from ..generic_payload.syft_message import RequestPayload
from .enum import EXECUTION_STATUS
from .enum import TASK_SERVICE_DEFAULT_MESSAGES
from .enum import TASK_SERVICE_FIELDS
from .enum import TASK_SERVICE_STATUS

# from RestrictedPython.Guards import safe_builtins
# from RestrictedPython import compile_restricted


@serializable(recursive_serde=True)
@final
class CreateTask(SyftMessage, DomainMessageRegistry):
    # Pydantic Inner class to define expected request payload fields.
    class Request(RequestPayload):
        """Payload fields and types used during a User Creation Request."""

        inputs: Dict[str, str]
        code: str
        policy_code: str
        policy_name: str
        outputs: List[str]

    # Pydantic Inner class to define expected reply payload fields.
    class Reply(ReplyPayload):
        """Payload fields and types used during a User Creation Response."""

        message: str = TASK_SERVICE_DEFAULT_MESSAGES.CREATE_TASK.value

    request_payload_type = (
        Request  # Converts generic syft dict into a CreateUserMessage.Request object.
    )
    reply_payload_type = (
        Reply  # Creates a proper Reply payload message structure as a response.
    )

    def run(  # type: ignore
        self, node: DomainInterface, verify_key: Optional[VerifyKey] = None
    ) -> ReplyPayload:  # type: ignore
        user = node.users.get_user(verify_key=verify_key)

        task = NoSQLTask(
            uid=UID().to_string(),
            user=user.id.to_string(),
            inputs=self.payload.inputs,
            outputs={var: " -- " for var in self.payload.outputs},
            owner={"name": user.name, "role": user.role["name"], "email": user.email},
            code=self.payload.code,
            policy_code=self.payload.policy_code,
            policy_name=self.payload.policy_name,
            state=str({}),
            status=TASK_SERVICE_STATUS.PENDING.value,
            created_at=date.today().strftime("%d/%m/%Y"),
            updated_at=" -- ",
            reviewed_by=" -- ",
            execution={
                TASK_SERVICE_FIELDS.STATUS.value: EXECUTION_STATUS.WAITING.value
            },
        )
        node.tasks.add(task)
        return CreateTask.Reply()

    def get_permissions(self) -> List[Type[BasePermission]]:
        """Returns the list of permission classes."""
        return [NoRestriction]


@serializable(recursive_serde=True)
@final
class GetTasks(SyftMessage, DomainMessageRegistry):
    # Pydantic Inner class to define expected request payload fields.
    class Request(RequestPayload):
        pass

    # Pydantic Inner class to define expected reply payload fields.
    class Reply(ReplyPayload):
        tasks: List[Dict[str, Any]]

    request_payload_type = (
        Request  # Converts generic syft dict into a CreateUserMessage.Request object.
    )
    reply_payload_type = (
        Reply  # Creates a proper Reply payload message structure as a response.
    )

    def run(  # type: ignore
        self, node: DomainInterface, verify_key: Optional[VerifyKey] = None
    ) -> ReplyPayload:  # type: ignore
        user = node.users.get_user(verify_key=verify_key)

        if user.role["name"] == node.roles.owner_role["name"]:
            tasks = node.tasks.all()
        else:
            tasks = node.tasks.find(
                search_params={TASK_SERVICE_FIELDS.USER.value: user.id.to_string()}
            )
        return GetTasks.Reply(tasks=tasks)

    def get_permissions(self) -> List[Type[BasePermission]]:
        """Returns the list of permission classes."""
        return [NoRestriction]


@serializable(recursive_serde=True)
@final
class GetTask(SyftMessage, DomainMessageRegistry):
    # Pydantic Inner class to define expected request payload fields.
    class Request(RequestPayload):
        task_uid: str

    # Pydantic Inner class to define expected reply payload fields.
    class Reply(ReplyPayload):
        code: str
        policy_code: str
        policy_name: str
        state: str
        status: str
        owner: Dict[str, str]
        created_at: str
        updated_at: str
        reviewed_by: str
        execution: Dict[str, str]
        uid: str
        reason: str
        inputs: Dict[str, str] = {}
        outputs: Dict[str, str] = {}

    request_payload_type = (
        Request  # Converts generic syft dict into a CreateUserMessage.Request object.
    )
    reply_payload_type = (
        Reply  # Creates a proper Reply payload message structure as a response.
    )

    def run(  # type: ignore
        self, node: DomainInterface, verify_key: Optional[VerifyKey] = None
    ) -> ReplyPayload:  # type: ignore
        user = node.users.get_user(verify_key=verify_key)
        if user.role["name"] == node.roles.owner_role["name"]:
            task = node.tasks.find_one(
                search_params={TASK_SERVICE_FIELDS.UID.value: self.payload.task_uid}
            )
        else:
            task = node.tasks.find_one(
                search_params={
                    TASK_SERVICE_FIELDS.USER.value: user.id.to_string(),
                    TASK_SERVICE_FIELDS.UID.value: self.payload.task_uid,
                }
            )

        return GetTask.Reply(**task)

    def get_permissions(self) -> List[Type[BasePermission]]:
        """Returns the list of permission classes."""
        return [NoRestriction]


@serializable(recursive_serde=True)
@final
class ReviewTask(SyftMessage, DomainMessageRegistry):
    # Pydantic Inner class to define expected request payload fields.
    class Request(RequestPayload):
        task_uid: str
        reason: str
        status: str

    # Pydantic Inner class to define expected reply payload fields.
    class Reply(ReplyPayload):
        message: str = TASK_SERVICE_DEFAULT_MESSAGES.REVIEW_TASK.value

    request_payload_type = (
        Request  # Converts generic syft dict into a CreateUserMessage.Request object.
    )
    reply_payload_type = (
        Reply  # Creates a proper Reply payload message structure as a response.
    )

    def run(  # type: ignore
        self, node: DomainInterface, verify_key: Optional[VerifyKey] = None
    ) -> ReplyPayload:  # type: ignore
        user = node.users.get_user(verify_key=verify_key)

        status = self.payload.status.lower()

        # TODO change status to accepted or denied, not enqueued
        update_values = {
            TASK_SERVICE_FIELDS.STATUS.value: status,
            TASK_SERVICE_FIELDS.REASON.value: self.payload.reason,
            TASK_SERVICE_FIELDS.REVIEWED_BY.value: user.name,
            TASK_SERVICE_FIELDS.UPDATED_AT.value: date.today().strftime("%d/%m/%Y"),
            TASK_SERVICE_FIELDS.EXECUTION.value: {"status": "not executing"}
            if status != TASK_SERVICE_STATUS.ACCEPTED.value
            else {TASK_SERVICE_FIELDS.STATUS.value: EXECUTION_STATUS.ENQUEUED.value}, 
        }

        node.tasks.update(
            search_params={TASK_SERVICE_FIELDS.UID.value: self.payload.task_uid},
            updated_args=update_values,
        )
        
        task = node.tasks.find(search_params={"uid": self.payload.task_uid})
        if not task:
            raise Exception(f"The given task_id:{self.payload.task_uid} does not exist")
        task = task[0]

        init_state = init_policy_state(task.policy_code, task.policy_name)
        # TODO use our better serialization for the state variable
        
        node.tasks.update(
            search_params={"uid": task.uid},
            # updated_args={
            #     "execution": {"status": "executing"},
            # },
            updated_args={
                "state": str(init_state) 
            }
        )
        # execute_task(node, task.uid, task.code, task.inputs, task.outputs)

        return ReviewTask.Reply()

    def get_permissions(self) -> List[Type[BasePermission]]:
        """Returns the list of permission classes."""
        return [UserIsOwner]



@serializable(recursive_serde=True)
@final
class RunTask(SyftMessage, DomainMessageRegistry):

    # Pydantic Inner class to define expected request payload fields.
    class Request(RequestPayload):
        task_uid: str
        policy_args: str
        
    # Pydantic Inner class to define expected reply payload fields.
    class Reply(ReplyPayload):
        outputs: Dict[str, str]

    request_payload_type = (
        Request  # Converts generic syft dict into a CreateUserMessage.Request object.
    )
    reply_payload_type = (
        Reply  # Creates a proper Reply payload message structure as a response.
    )

    def run(  # type: ignore
        self, node: DomainInterface, verify_key: Optional[VerifyKey] = None
    ) -> ReplyPayload:  # type: ignore
        user = node.users.get_user(verify_key=verify_key)
        task = node.tasks.find(search_params={"uid": self.payload.task_uid})
        if not task:
            raise Exception(f"The given task_id:{self.payload.task_uid} does not exist")
        task = task[0]
        if task.user != user.id.to_string(): # TODO find a better wayt to check this
            raise Exception(f"User {user.id.to_string()} does not have access to task {task.uid}")
        
        # if task.status != EXECUTION_STATUS.ENQUEUED.value:
        #     raise Exception(f"Task {task.uid} not approved")
        
        outputs = execute_task(node, task.uid, task.code, task.inputs, self.payload.outputs)
    
        # TODO deserialize state   
        print(task.state)
        deserialized_state = eval(task.state)
        print(deserialized_state)
        outputs, state = apply_policy(
                            outputs, 
                            task.policy_code, 
                            task.policy_name, 
                            deserialized_state,
                            task.policy_args
                        )
        
        # TODO update state
        serialized_state = str(state)
        node.tasks.update(
            search_params={"uid": task.uid},
            updated_args={
                "state": serialized_state,
            },
        )
        return RunTask.Reply(outputs=outputs)

    def get_permissions(self) -> List[Type[BasePermission]]:
        """Returns the list of permission classes."""
        return [UserIsOwner]

# TODO: Figure what to do when the policy code is using object outside our context
def get_policy(policy_code, policy_name):
    print(policy_code)
    import syft as sy
    exec(policy_code)
    print(vars().keys())
    policy_class = eval(policy_name)
    # de_policy_args = eval(policy_args)
    return policy_class() #TODO: add args

def init_policy_state(policy_code, policy_name):
    policy_obj = get_policy(policy_code, policy_name)
    policy_obj.start()
    return policy_obj.state

def apply_policy(outputs, policy_code, policy_name, state, policy_args):
    policy_obj = get_policy(policy_code, policy_name)
    policy_obj.set_state(state)
    policy_args_dict = eval(policy_args)
    new_outputs = policy_obj.apply_output(outputs, **policy_args_dict) # TODO: add kwargs
    new_state = policy_obj.state
    return new_outputs, new_state

stdout_ = sys.stdout
stderr_ = sys.stderr


def execute_task(
    node: AbstractNode,
    task_uid: str,
    code: str,
    inputs: Dict[str, str],
    outputs: Dict[str, str],
) -> None:
    global stdout_
    global stderr_
    try:
        logger.info(f"inital outputs: {outputs}")
        node.tasks.update(
            search_params={"uid": task_uid},
            updated_args={"execution": {"status": "executing"}},
        )

        # Check overlap between inputs and vars
        global_input_inter = set(globals().keys()).intersection(set(inputs.keys()))
        local_input_inter = set(vars().keys()).intersection(set(inputs.keys()))

        # If there's some intersection between global variables and input
        if global_input_inter or local_input_inter:
            stderr_message = " You can't use variable name: "
            stderr_message += ",".join(list(global_input_inter))
            stderr_message += ",".join(list(local_input_inter))

            node.tasks.update(
                search_params={"uid": task_uid},
                updated_args={
                    "execution": {"status": "failed", "stderr": stderr_message}
                },
            )
            return None

        local_vars = {}
        for key, value in inputs.items():
            local_vars[key] = node.store.get(value, proxy_only=True).data

        # create file-like string to capture ouputs
        codeOut = StringIO()
        codeErr = StringIO()

        sys.stdout = codeOut
        sys.stderr = codeErr

        locals().update(local_vars)
        # byte_code = compile_restricted(code, "<string>", "exec")
        # exec(byte_code, restricted_globals)
        exec(code)  # nosec

        for output in outputs:
            logger.info(f"variable: {output} result: {vars()[output]}")
            outputs[output] = vars()[output]

        # restore stdout and stderr
        sys.stdout = stdout_
        sys.stderr = stderr_

        logger.info(outputs)

        logger.info("Error: " + str(codeErr.getvalue()))
        logger.info("Std ouputs: " + str(codeOut.getvalue()))

        new_id = UID()
        node.store.check_collision(new_id)

        obj = StorableObject(
            id=new_id,
            data=outputs,
            search_permissions={VERIFYALL: None},
        )

        obj.read_permissions = {
            node.verify_key: node.id,
        }

        obj.write_permissions = {
            node.verify_key: node.id,
        }

        node.store[new_id] = obj

        node.tasks.update(
            search_params={"uid": task_uid},
            updated_args={
                "execution": {"status": "done"},
                "outputs": {"output": new_id.to_string()}, # TODO change this to be more readable
            },
        )
        return {"output": new_id.to_string()}
    except Exception as e:
        sys.stdout = stdout_
        sys.stderr = stderr_
        print("Task Failed with Exception", e)
    finally:
        sys.stdout = stdout_
        sys.stderr = stderr_
