from setuptools import setup

package_name = 'soundbox_palletizer'

setup(
    name=package_name,
    version='0.1.0',
    packages=[package_name],
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/launch', ['launch/palletizer.launch.py']),
        ('share/' + package_name + '/config', ['config/palletizer_params.yaml']),
    ],
    install_requires=['setuptools', 'requests'],
    zip_safe=True,
    maintainer='Isaac Martins',
    maintainer_email='isaac.martins@example.com',
    description='SoundBox Pallet Optimizer ROS2 node',
    license='MIT',
    entry_points={
        'console_scripts': [
            'coordinate_publisher = soundbox_palletizer.coordinate_publisher:main',
            'pallet_visualizer = soundbox_palletizer.pallet_visualizer:main',
        ],
    },
)
