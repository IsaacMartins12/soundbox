#!/bin/bash

# Substituir todos os $(find ...) por paths absolutos em todos os arquivos

# 1. Corrigir common_materials.xacro
sed -e 's|$(find motoman_resources)|/ros2_ws/src/motoman_resources|g' \
    -e 's|$(find motoman_gp88_support)|/ros2_ws/src/motoman_gp88_support|g' \
    /ros2_ws/src/motoman_resources/urdf/common_materials.xacro > /tmp/common_materials_fixed.xacro

# 2. Corrigir gp88_macro.xacro
sed -e 's|$(find motoman_gp88_support)|/ros2_ws/src/motoman_gp88_support|g' \
    -e 's|$(find motoman_resources)|/ros2_ws/src/motoman_resources|g' \
    /ros2_ws/src/motoman_gp88_support/urdf/gp88_macro.xacro > /tmp/gp88_macro_fixed.xacro

# 3. Substituir includes no macro para apontar para os fixados
sed -i 's|/ros2_ws/src/motoman_resources/urdf/common_materials.xacro|/tmp/common_materials_fixed.xacro|g' /tmp/gp88_macro_fixed.xacro

# 4. Criar xacro principal
cat > /tmp/gp88_fixed.xacro << 'EOF'
<?xml version="1.0" ?>
<robot name="motoman_gp88" xmlns:xacro="http://ros.org/wiki/xacro">
  <xacro:include filename="/tmp/gp88_macro_fixed.xacro" />
  <xacro:motoman_gp88 prefix=""/>
</robot>
EOF

# 5. Gerar URDF
source /opt/ros/humble/setup.bash
xacro /tmp/gp88_fixed.xacro > /tmp/gp88.urdf 2>&1

echo "=== RESULTADO ==="
if [ -s /tmp/gp88.urdf ] && [ $(wc -l < /tmp/gp88.urdf) -gt 5 ]; then
    echo "URDF gerado com sucesso!"
    echo "Linhas: $(wc -l < /tmp/gp88.urdf)"
    head -5 /tmp/gp88.urdf
else
    echo "ERRO:"
    cat /tmp/gp88.urdf
fi
