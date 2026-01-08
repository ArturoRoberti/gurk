check_install_ros() {
	: '
	Check if ROS (ROS1 or ROS2) is installed.

	Args:
	  None
	Outputs:
	  Path to the roscore or ros2 executable if installed.
	Returns:
	  0 if installed, 1 otherwise
	'
	local setup_script=""
	if [[ -d "/opt/ros/" ]]; then
		setup_script=$(sudo find /opt/ros/ -name "setup.bash" | head -n1)
	fi
	if [[ -f "$setup_script" ]]; then
		ros_path=$(source "$setup_script" && command -v roscore || command -v ros2)
		if [ -n "$ros_path" ]; then
			echo "$ros_path"
			return 0
		else
			return 1
		fi
	else
		return 1
	fi
}
