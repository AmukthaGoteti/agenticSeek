import sys
import os
import configparser
from abc import abstractmethod

# Ensure logger can be imported when running as a script or as part of a larger project
if __name__ == "__main__":
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sources.logger import Logger

class Tools():
    """
    Abstract class for all tools.
    """
    def __init__(self):
        self.tag = "undefined"
        self.name = "undefined"
        self.description = "undefined"
        self.client = None
        self.messages = []
        self.logger = Logger("tools.log")
        self.config = configparser.ConfigParser()
        self._work_dir_initialized = False # Flag to ensure work_dir setup runs only once
        self.work_dir = self.safe_get_work_dir_path() # Initialize work_dir safely
        self.excutable_blocks_found = False
        self.safe_mode = True
        self.allow_language_exec_bash = False
    
    def get_work_dir(self):
        """
        Returns the path to the working directory.
        Ensures the work directory is initialized if it hasn't been already.
        """
        if not self._work_dir_initialized:
            self.work_dir = self.safe_get_work_dir_path()
        return self.work_dir
    
    def set_allow_language_exec_bash(self, value: bool) -> None:
        """
        Sets the flag to allow or disallow bash execution for language tools.
        Args:
            value (bool): True to allow, False to disallow.
        """
        self.allow_language_exec_bash = value 

    def config_exists(self):
        """Check if the config file exists."""
        return os.path.exists('./config.ini')

    def _initialize_work_dir(self) -> str:
        """
        Internal method to determine and create the work directory path.
        This method is called only when the work directory needs to be set up.
        """
        default_path = os.path.dirname(os.getcwd())
        path = None

        # 1. Try to get work_dir from environment variable
        path = os.getenv('WORK_DIR', None)

        # 2. If not in env, try to get from config file
        if path is None and self.config_exists():
            self.config.read('./config.ini')
            if 'MAIN' in self.config and 'work_dir' in self.config['MAIN']:
                path = self.config['MAIN']['work_dir']
        
        # 3. If still not found, use default path
        if path is None or path == "":
            print("No work directory specified, using default based on current working directory.")
            self.logger.warning("No WORK_DIR environment variable or 'work_dir' in config.ini found. Using default path.")
            path = default_path

        # Create the directory if it doesn't exist
        if not os.path.exists(path):
            try:
                os.makedirs(path, exist_ok=True) # exist_ok=True prevents error if dir already exists
                self.logger.info(f"Created work directory at: {path}")
            except OSError as e:
                self.logger.error(f"Error creating work directory '{path}': {e}")
                # Fallback or raise an error if directory creation fails critically
                raise
        
        self._work_dir_initialized = True
        return path

    def safe_get_work_dir_path(self) -> str:
        """
        Safely retrieves the work directory path.
        If the work directory hasn't been initialized, it initializes it.
        This acts as the public interface for getting the work directory.
        """
        if not self._work_dir_initialized:
            self.work_dir = self._initialize_work_dir()
        return self.work_dir

    @abstractmethod
    def execute(self, blocks:[str], safety:bool) -> str:
        """
        Abstract method that must be implemented by child classes to execute the tool's functionality.
        Args:
            blocks (List[str]): The codes or queries blocks to execute
            safety (bool): Whenever human intervention is required
        Returns:
            str: The output/result from executing the tool
        """
        pass

    @abstractmethod
    def execution_failure_check(self, output:str) -> bool:
        """
        Abstract method that must be implemented by child classes to check if tool execution failed.
        Args:
            output (str): The output string from the tool execution to analyze
        Returns:
            bool: True if execution failed, False if successful
        """
        pass

    @abstractmethod
    def interpreter_feedback(self, output:str) -> str:
        """
        Abstract method that must be implemented by child classes to provide feedback to the AI from the tool.
        Args:
            output (str): The output string from the tool execution to analyze
        Returns:
            str: The feedback message to the AI
        """
        pass

    def save_block(self, blocks:[str], save_path:str) -> None:
        """
        Save code or query blocks to a file at the specified path.
        Creates the directory path if it doesn't exist.
        Args:
            blocks (List[str]): List of code/query blocks to save
            save_path (str): File path where blocks should be saved
        """
        if save_path is None:
            return
        
        # Ensure work_dir is set before using it
        base_work_dir = self.get_work_dir() 

        self.logger.info(f"Saving blocks to {save_path} within work directory: {base_work_dir}")
        
        save_path_dir = os.path.dirname(save_path)
        save_path_file = os.path.basename(save_path)
        
        # Combine base_work_dir with the directory from save_path
        directory_to_create = os.path.join(base_work_dir, save_path_dir)
        
        if directory_to_create and not os.path.exists(directory_to_create):
            self.logger.info(f"Creating directory {directory_to_create}")
            os.makedirs(directory_to_create, exist_ok=True) # Ensure it's created safely
        
        full_file_path = os.path.join(directory_to_create, save_path_file)
        try:
            with open(full_file_path, 'w') as f:
                for block in blocks:
                    f.write(block)
                    if not block.endswith('\n'): # Add newline if not present
                        f.write('\n') 
            self.logger.info(f"Successfully saved blocks to {full_file_path}")
        except IOError as e:
            self.logger.error(f"Error saving blocks to {full_file_path}: {e}")
            raise # Re-raise to indicate failure

    def get_parameter_value(self, block: str, parameter_name: str) -> str | None:
        """
        Get a parameter name.
        Args:
            block (str): The block of text to search for the parameter
            parameter_name (str): The name of the parameter to retrieve
        Returns:
            str: The value of the parameter, or None if not found.
        """
        for param_line in block.split('\n'):
            if parameter_name in param_line:
                parts = param_line.split('=', 1) # Split only on the first '='
                if len(parts) > 1:
                    return parts[1].strip()
        return None
    
    def found_executable_blocks(self) -> bool:
        """
        Check if executable blocks were found in the last `load_exec_block` call.
        Resets the flag after checking.
        Returns:
            bool: True if executable blocks were found, False otherwise.
        """
        tmp = self.excutable_blocks_found
        self.excutable_blocks_found = False # Reset the flag
        return tmp

    def load_exec_block(self, llm_text: str) -> tuple[list[str], str | None]:
        """
        Extract code/query blocks from LLM-generated text and process them for execution.
        This method parses the text looking for code blocks marked with the tool's tag (e.g. ```python).
        Args:
            llm_text (str): The raw text containing code blocks from the LLM
        Returns:
            tuple[list[str], str | None]: A tuple containing:
                - List of extracted and processed code blocks
                - The path the code blocks was saved to
        """
        if self.tag == "undefined":
            self.logger.error("Tool tag is 'undefined'. Cannot load executable blocks.")
            assert False, "Tag not defined"
            
        start_tag = f'```{self.tag}' 
        end_tag = '```'
        code_blocks = []
        start_index = 0
        save_path = None

        if start_tag not in llm_text:
            return [], None # Return empty list, not None, to be consistent with type hint

        while True:
            start_pos = llm_text.find(start_tag, start_index)
            if start_pos == -1:
                break

            # Find the start of the line containing start_tag to check for leading whitespace
            line_start = llm_text.rfind('\n', 0, start_pos) + 1
            leading_whitespace = llm_text[line_start:start_pos]

            end_pos = llm_text.find(end_tag, start_pos + len(start_tag))
            if end_pos == -1:
                # If an opening tag is found but no closing tag, break to avoid infinite loop
                break 
            
            content = llm_text[start_pos + len(start_tag):end_pos]
            
            # Remove leading whitespace from each line if the block itself is indented
            if leading_whitespace:
                lines = content.split('\n')
                processed_lines = []
                for line in lines:
                    if line.startswith(leading_whitespace):
                        processed_lines.append(line[len(leading_whitespace):])
                    else:
                        processed_lines.append(line)
                content = '\n'.join(processed_lines)

            # Check for save_path in the first line of the block content
            first_line = content.split('\n', 1)[0] # Get only the first line
            if first_line.startswith('save_path='): # A more robust check for a parameter
                save_path = first_line.split('=', 1)[1].strip()
                content = content[len(first_line):].lstrip('\n') # Remove the save_path line and any leading newline
            elif ':' in first_line and ' ' not in first_line: # Original logic for colon separated path
                # This check might be too broad; consider if "param:value" is specific enough
                potential_path = first_line.split(':', 1)[1]
                # Add validation for potential_path to ensure it's a valid path format
                if potential_path: # Basic check
                   save_path = potential_path.strip()
                   content = content[content.find('\n')+1:] # Remove the path line


            self.excutable_blocks_found = True
            code_blocks.append(content)
            start_index = end_pos + len(end_tag)
            
        self.logger.info(f"Found {len(code_blocks)} blocks to execute")
        return code_blocks, save_path
    
# --- Example Usage (for testing) ---
if __name__ == "__main__":
    # Create a dummy config.ini for testing purposes
    # This simulates how your application might set up a config
    if not os.path.exists('config.ini'):
        with open('config.ini', 'w') as f:
            f.write('[MAIN]\n')
            f.write('work_dir = ./test_work_dir\n')
    
    print("--- Testing Tools Class Initialization and Work Dir Handling ---")
    tool = Tools()
    print(f"Tool initialized. Work directory: {tool.get_work_dir()}")
    print(f"Is work directory initialized flag set? {tool._work_dir_initialized}")

    # Test re-getting work dir
    another_tool_instance = Tools() # Simulate another instance
    print(f"Another tool instance work directory: {another_tool_instance.get_work_dir()}")

    # Test load_exec_block functionality
    print("\n--- Testing load_exec_block ---")
    tool.tag = "python" # Set the tool's tag