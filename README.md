# Terraform Operator Tasks

When a terraform operator resource is created, a workflow is kicked off which calls a series of tasks. Tasks are pods that run scripts defined by the user.

The scripts here are, in most cases, enough to satisfy the most common use case of terraform operator workflow.

## Pod Container Images

The [images](images) directory contains the container image build tools for the tasks. There are generally three types of tasks:

1. Setup
2. Terraform
3. Script

### Image Builds

The provided scripts in [images](images) is an aid in creating container images. Each team or user will need to provide their own container registries.

#### Setup Image

This image a lightweight image suited for performing git clones and wgets of http sources. It generally executes the `setup.sh`

#### Terraform Image

The default image contains the specific terraform version defined in the terraform operator resource; `spec.terraformVersion`

If a custom terraform image is built, the tag MUST match the `spec.terraformVersion` defined.

#### Script Image

This is an all-purpose image that can execute scripts defined by the user. The default image contains a large toolset but is likely missing binaries for advanced users.



## Task Scripts

The task script is usually downloaded by the task container when it starts, and then executes the script immediately using the `exec` bash builtin command.

When customizing the scripts, terraform operator uses a common set of environment variables that get injected into every pod.

| Environment Variable Name | Description |
| --- | --- |
| `TFO_TASK` | The name of the task being executed. Will be one of the following: <br/><br/><ul><li>`setup`</li><li>`preinit`</li><li>`init`</li><li>`postinit`</li><li>`preplan`</li><li>`plan`</li><li>`postplan`</li><li>`preapply`</li><li>`apply`</li><li>`postapply`</li></ul><br/><br/>When a terraform operator resource is deleted, users that have configured the resources created by terraform to be destroyed will have a set of tasks that match the following with a `-delete` suffix appended to the end of each task name. For example, when a delete-workflow beings, it will have a task name of `setup-delete` |
| `TFO_GENERATION_PATH` | The path inside the task container that points to the root of all the things that are created for the current generation. A "generation" the terraform operator resource configuration after it has been updated. Every update incurs a new generation, therefore a new workflow will begin. Use `TFO_GENERATION_PATH` to work only in the context of all things related to a particular configuration. |
| `TFO_MAIN_MODULE` | The path to the root of the terraform module. This is always `${TFO_GENERATION_PATH}/main`.

#### Setup Scripts

Setup is responsible for placing the terraform module at the `$TFO_MAIN_MODULE` location. It is also responsible for downloading resources and placing them according to their configuration.

**Default:** `setup.sh`


#### Terraform Scripts

Depending on the `$TFO_TASK`, the terraform's main function is to execute `terraform init`, `terraform plan` or `terraform apply` for the module in `$TFO_MAIN_MODULE`. Sometimes there are a few steps of configuration that must be done before executing the terraform commands.

**Default:** `tf.sh`


#### Scripts (in-between terraform workflow pods)

These are general scripts configured by the user for any purpose. The user should always try and work within the `$TFO_GENERATION_PATH` to avoid getting mixed up with data from other runs.

**No Default**


## Contributions

If you'd like to contribute, feel free to open a Pull Request or an Issue.