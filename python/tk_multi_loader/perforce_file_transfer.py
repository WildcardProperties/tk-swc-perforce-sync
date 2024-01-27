from your_module import connect  # Import the connect function from the provided module
import sgtk

class PerforceFileTransfer:
    def __init__(self, source_config, target_config):
        """
        Initialize the PerforceFileTransfer instance.

        :param source_config: Dictionary containing source Perforce configuration ('user', 'password', 'workspace').
        :param target_config: Dictionary containing target Perforce configuration ('user', 'password', 'workspace').
        """
        self.source_config = source_config
        self.target_config = target_config
        self.fw = None
        self.source_connection = None
        self.target_connection = None

    def connect_to_perforce(self):
        """
        Connect to both source and target Perforce repositories.
        """
        # Connect to the source Perforce repository
        self.fw = sgtk.platform.get_framework("tk-framework-perforce")
        self.source_connection = self.fw.connection.connect()
        # self.source_connection = connect(allow_ui=True, **self.source_config)
        if not self.source_connection:
            raise Exception("Failed to connect to the source repository.")

        # Connect to the target Perforce repository
        self.target_connection = connect(allow_ui=True, **self.target_config)
        if not self.target_connection:
            self.source_connection.disconnect()
            raise Exception("Failed to connect to the target repository.")

    def disconnect_from_perforce(self):
        """
        Disconnect from both source and target Perforce repositories.
        """
        if self.source_connection:
            self.source_connection.disconnect()

        if self.target_connection:
            self.target_connection.disconnect()

    def transfer_file(self, source_file, target_file):
        """
        Transfer a file from source Perforce repository to target repository.

        :param source_file: Path to the source file in the source Perforce repository.
        :param target_file: Path where the file should be stored in the target Perforce repository.
        """
        try:
            # Connect to Perforce servers
            self.connect_to_perforce()

            # Sync the specified file from the source repository to the local workspace
            self.source_connection.run_sync(source_file)
            print(f"Synced {source_file} from the source repository.")

            # Assuming the file is now in the local workspace, add the file to the target depot
            self.target_connection.run_add(target_file)
            print(f"Added {target_file} to the target repository.")

            # Submit the file to the target depot
            submit_description = f"Transferred {source_file} to {target_file}"
            self.target_connection.run_submit('-d', submit_description, target_file)
            print(f"Submitted {target_file} to the target repository.")

        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # Disconnect from the Perforce repositories
            self.disconnect_from_perforce()

    @staticmethod
    def example_usage():
        source_config = {
            'user': 'source_username',
            'password': 'source_password',
            'workspace': 'source_workspace'
        }

        target_config = {
            'user': 'target_username',
            'password': 'target_password',
            'workspace': 'target_workspace'
        }

        file_transfer = PerforceFileTransfer(source_config, target_config)
        file_transfer.transfer_file('//depot/path/to/source/file', '//depot/path/to/target/file')


# To run the example usage:
if __name__ == "__main__":
    PerforceFileTransfer.example_usage()
