#!/usr/bin/env python3
"""
硬件检测模块 - 自动检测电脑配置并推荐最优 Qwen3-ASR 配置
支持 Windows、macOS 和 Linux
"""

import platform
import subprocess
import sys
from typing import Dict, Tuple, Optional
import re


class HardwareDetector:
    """硬件检测和配置推荐类"""

    def __init__(self):
        self.system = platform.system()
        self.machine = platform.machine()
        self.processor = platform.processor()

    def detect_all(self) -> Dict:
        """
        检测所有硬件信息

        Returns:
            包含硬件信息的字典
        """
        hardware_info = {
            "system": self.system,
            "machine": self.machine,
            "processor": self.processor,
            "cpu_cores": None,
            "memory_gb": None,
            "gpu": [],
            "has_nvidia_gpu": False,
            "has_amd_gpu": False,
            "has_apple_silicon": False,
        }

        # 检测 CPU 核心数和内存
        hardware_info["cpu_cores"] = self._get_cpu_cores()
        hardware_info["memory_gb"] = self._get_memory()

        # 检测 GPU
        hardware_info["gpu"] = self._detect_gpu()
        hardware_info["has_nvidia_gpu"] = any(
            "nvidia" in gpu.lower() for gpu in hardware_info["gpu"]
        )
        hardware_info["has_amd_gpu"] = any(
            "amd" in gpu.lower() or "radeon" in gpu.lower()
            for gpu in hardware_info["gpu"]
        )
        hardware_info["has_apple_silicon"] = self._is_apple_silicon()

        return hardware_info

    def _is_apple_silicon(self) -> bool:
        """检测是否为 Apple Silicon 芯片"""
        if self.system == "Darwin":
            if self.machine in ["arm64", "arm"]:
                return True
            # 检查处理器信息
            if self.processor and (
                "apple" in self.processor.lower()
                or "m1" in self.processor.lower()
                or "m2" in self.processor.lower()
                or "m3" in self.processor.lower()
            ):
                return True
        return False

    def _get_cpu_cores(self) -> int:
        """获取 CPU 核心数"""
        try:
            if self.system == "Darwin":  # macOS
                result = subprocess.run(
                    ["sysctl", "-n", "hw.ncpu"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                return int(result.stdout.strip())
            elif self.system == "Linux":
                return os.cpu_count()
            elif self.system == "Windows":
                result = subprocess.run(
                    ["wmic", "cpu", "get", "NumberOfCores"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                # 解析 Windows 输出
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if line.strip().isdigit():
                        return int(line.strip())
            return os.cpu_count()
        except:
            return os.cpu_count() or 4

    def _get_memory(self) -> int:
        """获取系统内存（GB）"""
        try:
            import psutil
            return psutil.virtual_memory().total // (1024**3)
        except ImportError:
            # 备用方案
            try:
                if self.system == "Darwin":  # macOS
                    result = subprocess.run(
                        ["sysctl", "-n", "hw.memsize"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    return int(result.stdout.strip()) // (1024**3)
                elif self.system == "Linux":
                    with open("/proc/meminfo", "r") as f:
                        for line in f:
                            if line.startswith("MemTotal:"):
                                kb = int(line.split()[1])
                                return kb // (1024**2)
                elif self.system == "Windows":
                    result = subprocess.run(
                        ["wmic", "memorychip", "get", "capacity"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    # 解析 Windows 输出并求和
                    total = 0
                    for line in result.stdout.strip().split('\n'):
                        if line.strip().isdigit():
                            total += int(line.strip())
                    return total // (1024**3)
            except:
                pass
        except:
            pass
        return 8  # 默认返回 8GB

    def _detect_gpu(self) -> list:
        """检测 GPU 信息"""
        gpus = []

        try:
            if self.system == "Darwin":  # macOS
                # 检测 Apple Silicon GPU
                if self._is_apple_silicon():
                    chip = self._get_apple_chip_name()
                    if chip:
                        gpus.append(f"Apple {chip} GPU")
                # 检测其他 GPU
                result = subprocess.run(
                    ["system_profiler", "SPDisplaysDataType"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                output = result.stdout
                # 解析 macOS GPU 信息
                for line in output.split('\n'):
                    if 'Chipset Model' in line or 'VRAM' in line:
                        gpu_info = line.split(':')[1].strip() if ':' in line else line.strip()
                        if gpu_info and gpu_info not in gpus:
                            gpus.append(gpu_info)

            elif self.system == "Linux":
                # 检测 NVIDIA GPU
                try:
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                gpus.append(f"NVIDIA {line.strip()}")
                except FileNotFoundError:
                    pass

                # 检测 AMD GPU
                try:
                    result = subprocess.run(
                        ["rocm-smi", "--showproductname"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.split('\n'):
                            if 'GPU' in line and 'Card Series' in line:
                                gpus.append(f"AMD {line.strip()}")
                except FileNotFoundError:
                    pass

                # 从 lspci 检测
                try:
                    result = subprocess.run(
                        ["lspci"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    for line in result.stdout.split('\n'):
                        if 'VGA compatible controller' in line:
                            gpus.append(line.split(':')[3].strip() if len(line.split(':')) > 3 else line.strip())
                        elif 'Display' in line and 'NVIDIA' in line:
                            gpus.append(line.strip())
                except FileNotFoundError:
                    pass

            elif self.system == "Windows":
                # 检测 NVIDIA GPU
                try:
                    result = subprocess.run(
                        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        for line in result.stdout.strip().split('\n'):
                            if line.strip():
                                gpus.append(f"NVIDIA {line.strip()}")
                except FileNotFoundError:
                    pass

                # 使用 WMIC 检测 GPU
                try:
                    result = subprocess.run(
                        ["wmic", "path", "win32_VideoController", "get", "name"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    for line in result.stdout.strip().split('\n'):
                        line = line.strip()
                        if line and line != "Name":
                            if "NVIDIA" in line:
                                gpus.append(f"NVIDIA {line}")
                            elif "AMD" in line or "Radeon" in line:
                                gpus.append(f"AMD {line}")
                            elif "Intel" in line:
                                gpus.append(f"Intel {line}")
                            else:
                                gpus.append(line)
                except:
                    pass

        except Exception as e:
            pass

        # 去重
        seen = set()
        unique_gpus = []
        for gpu in gpus:
            gpu_lower = gpu.lower()
            if gpu_lower not in seen:
                seen.add(gpu_lower)
                unique_gpus.append(gpu)

        return unique_gpus if unique_gpus else ["Unknown GPU"]

    def _get_apple_chip_name(self) -> Optional[str]:
        """获取 Apple 芯片名称（M1/M2/M3 等）"""
        try:
            result = subprocess.run(
                ["sysctl", "-n", "machdep.cpu.brand_string"],
                capture_output=True,
                text=True,
                timeout=5
            )
            brand = result.stdout.strip()
            # 提取 M1/M2/M3 等信息
            match = re.search(r'M[1-5]\s*\w*', brand, re.IGNORECASE)
            if match:
                return match.group(0).upper()
            return None
        except:
            return None

    def recommend_whisper_config(self, hardware_info: Dict = None) -> Dict:
        """
        根据硬件信息推荐最优 Whisper 配置

        Args:
            hardware_info: 硬件信息字典，如果为 None 则自动检测

        Returns:
            推荐配置字典
        """
        if hardware_info is None:
            hardware_info = self.detect_all()

        config = {
            "model_size": "medium",
            "device": "cpu",
            "compute_type": "default",
            "batch_size": 16,
            "reason": "",
            "estimated_speedup": "1x (基准)",
        }

        # 检测 NVIDIA GPU（最优方案）
        if hardware_info["has_nvidia_gpu"]:
            config.update({
                "model_size": "large-v3-turbo",  # 最新的 turbo 模型
                "device": "cuda",
                "compute_type": "float16",  # GPU 推荐 float16
                "batch_size": 32,
                "reason": f"检测到 NVIDIA GPU: {hardware_info['gpu'][0]}",
                "estimated_speedup": "10-20x (相比 CPU medium)",
            })
            return config

        # 检测 Apple Silicon（次优方案）
        if hardware_info["has_apple_silicon"]:
            # macOS 上 faster-whisper 对 MPS 支持有限，推荐 CPU + turbo 模型
            config.update({
                "model_size": "large-v3-turbo",
                "device": "cpu",  # faster-whisper 在 macOS 上使用 CPU 更稳定
                "compute_type": "float32",
                "batch_size": 24,
                "reason": f"检测到 Apple Silicon: {hardware_info['processor']}, 使用优化后的 turbo 模型",
                "estimated_speedup": "2-3x (相比 medium)",
            })
            return config

        # 检测 AMD GPU（Linux ROCm 支持）
        if hardware_info["has_amd_gpu"] and hardware_info["system"] == "Linux":
            # AMD GPU 在 Linux 上可能支持 ROCm
            try:
                import torch
                if torch.cuda.is_available():
                    config.update({
                        "model_size": "large-v3-turbo",
                        "device": "cuda",  # ROCm 使用 CUDA 接口
                        "compute_type": "float16",
                        "batch_size": 32,
                        "reason": f"检测到 AMD GPU (ROCm): {hardware_info['gpu'][0]}",
                        "estimated_speedup": "5-10x (相比 CPU)",
                    })
                    return config
            except ImportError:
                pass

        # CPU 优化方案
        memory_gb = hardware_info.get("memory_gb", 8)
        cpu_cores = hardware_info.get("cpu_cores", 4)

        if memory_gb >= 16 and cpu_cores >= 8:
            # 高配 CPU
            config.update({
                "model_size": "large-v3-turbo",
                "device": "cpu",
                "compute_type": "int8",  # int8 量化加速
                "batch_size": 16,
                "reason": f"高配 CPU ({cpu_cores} 核, {memory_gb}GB RAM), 使用 turbo+int8",
                "estimated_speedup": "2-3x (相比 medium)",
            })
        elif memory_gb >= 8:
            # 中配 CPU
            config.update({
                "model_size": "medium",
                "device": "cpu",
                "compute_type": "int8",
                "batch_size": 16,
                "reason": f"标准配置 CPU ({cpu_cores} 核, {memory_gb}GB RAM), 使用 medium+int8",
                "estimated_speedup": "1.5-2x (相比 medium float32)",
            })
        else:
            # 低配 CPU
            config.update({
                "model_size": "small",
                "device": "cpu",
                "compute_type": "int8",
                "batch_size": 8,
                "reason": f"低配 CPU，使用 small 模型确保稳定性",
                "estimated_speedup": "1.5-2x (相比 medium)",
            })

        return config

    def recommend_qwen_asr_config(self, hardware_info: Dict = None) -> Dict:
        """
        根据硬件信息推荐最优 Qwen3-ASR 配置

        Args:
            hardware_info: 硬件信息字典，如果为 None 则自动检测

        Returns:
            推荐配置字典，包含 model, device, dtype, reason, estimated_speedup
        """
        if hardware_info is None:
            hardware_info = self.detect_all()

        config = {
            "model": "Qwen/Qwen3-ASR-1.7B",
            "device": "cpu",
            "dtype": "float32",
            "reason": "",
            "estimated_speedup": "1x (基准)",
        }

        # 检测 NVIDIA GPU（最优方案）
        if hardware_info["has_nvidia_gpu"]:
            config.update({
                "model": "Qwen/Qwen3-ASR-1.7B",
                "device": "cuda",
                "dtype": "bfloat16",  # 官方推荐 bfloat16，模型权重格式为 BF16
                "reason": f"检测到 NVIDIA GPU: {hardware_info['gpu'][0]}",
                "estimated_speedup": "10-20x (相比 CPU)",
            })
            return config

        # 检测 Apple Silicon（M1/M2/M3/M5）
        if hardware_info["has_apple_silicon"]:
            # macOS 上优先尝试 MPS，回退到 CPU
            # 检查是否支持 MPS
            try:
                import torch
                if torch.backends.mps.is_available():
                    config.update({
                        "model": "Qwen/Qwen3-ASR-1.7B",
                        "device": "mps",
                        "dtype": "bfloat16",  # 官方推荐 bfloat16（M1+ 均支持 bfloat16）
                        "reason": f"检测到 Apple Silicon: {hardware_info['processor']}, 使用 MPS 加速",
                        "estimated_speedup": "3-5x (相比 CPU)",
                    })
                else:
                    config.update({
                        "model": "Qwen/Qwen3-ASR-1.7B",
                        "device": "cpu",
                        "dtype": "float32",
                        "reason": f"检测到 Apple Silicon: {hardware_info['processor']}, MPS 不可用，使用 CPU",
                        "estimated_speedup": "1.5-2x (相比低配 CPU)",
                    })
            except ImportError:
                config.update({
                    "model": "Qwen/Qwen3-ASR-1.7B",
                    "device": "cpu",
                    "dtype": "float32",
                    "reason": f"检测到 Apple Silicon: {hardware_info['processor']}, 使用 CPU",
                    "estimated_speedup": "1.5-2x (相比低配 CPU)",
                })
            return config

        # 检测 AMD GPU（Linux ROCm 支持）
        if hardware_info["has_amd_gpu"] and hardware_info["system"] == "Linux":
            # AMD GPU 在 Linux 上可能支持 ROCm
            try:
                import torch
                if torch.cuda.is_available():
                    config.update({
                        "model": "Qwen/Qwen3-ASR-1.7B",
                        "device": "cuda",  # ROCm 使用 CUDA 接口
                        "dtype": "bfloat16",  # 官方推荐 bfloat16
                        "reason": f"检测到 AMD GPU (ROCm): {hardware_info['gpu'][0]}",
                        "estimated_speedup": "5-10x (相比 CPU)",
                    })
                    return config
            except ImportError:
                pass

        # CPU 优化方案
        memory_gb = hardware_info.get("memory_gb", 8)
        cpu_cores = hardware_info.get("cpu_cores", 4)

        if memory_gb >= 16 and cpu_cores >= 8:
            # 高配 CPU
            config.update({
                "model": "Qwen/Qwen3-ASR-1.7B",
                "device": "cpu",
                "dtype": "float32",
                "reason": f"高配 CPU ({cpu_cores} 核, {memory_gb}GB RAM), 使用 1.7B 模型",
                "estimated_speedup": "1.5-2x (相比低配 CPU)",
            })
        elif memory_gb >= 8:
            # 中配 CPU
            config.update({
                "model": "Qwen/Qwen3-ASR-1.7B",
                "device": "cpu",
                "dtype": "float32",
                "reason": f"标准配置 CPU ({cpu_cores} 核, {memory_gb}GB RAM), 使用 1.7B 模型",
                "estimated_speedup": "1.5x (相比低配 CPU)",
            })
        else:
            # 低配 CPU - 使用 0.6B 模型
            config.update({
                "model": "Qwen/Qwen3-ASR-0.6B",
                "device": "cpu",
                "dtype": "float32",
                "reason": f"低配 CPU，使用 0.6B 模型确保稳定性",
                "estimated_speedup": "2-3x (相比 1.7B 模型)",
            })

        return config

    def print_hardware_info(self, hardware_info: Dict = None):
        """打印硬件信息"""
        if hardware_info is None:
            hardware_info = self.detect_all()

        print("\n" + "=" * 60)
        print("硬件检测结果")
        print("=" * 60)
        print(f"操作系统: {hardware_info['system']}")
        print(f"架构: {hardware_info['machine']}")
        print(f"处理器: {hardware_info['processor']}")
        print(f"CPU 核心数: {hardware_info['cpu_cores']}")
        print(f"内存: {hardware_info['memory_gb']} GB")
        print(f"GPU: {', '.join(hardware_info['gpu']) if hardware_info['gpu'] else '未检测到'}")
        print(f"Apple Silicon: {'是' if hardware_info['has_apple_silicon'] else '否'}")
        print(f"NVIDIA GPU: {'是' if hardware_info['has_nvidia_gpu'] else '否'}")
        print(f"AMD GPU: {'是' if hardware_info['has_amd_gpu'] else '否'}")
        print("=" * 60 + "\n")

    def print_recommended_config(self, config: Dict):
        """打印推荐配置"""
        print("\n" + "=" * 60)
        print("推荐配置")
        print("=" * 60)
        if "model_size" in config:  # Whisper 配置
            print(f"模型: {config['model_size']}")
            print(f"设备: {config['device']}")
            print(f"计算类型: {config['compute_type']}")
            print(f"批处理大小: {config['batch_size']}")
        else:  # Qwen3-ASR 配置
            print(f"模型: {config['model']}")
            print(f"设备: {config['device']}")
            print(f"数据类型: {config.get('dtype', 'float32')}")
        print(f"原因: {config['reason']}")
        print(f"预期加速: {config['estimated_speedup']}")
        print("=" * 60 + "\n")


def main():
    """主函数 - 演示硬件检测"""
    detector = HardwareDetector()

    # 检测硬件
    hardware_info = detector.detect_all()
    detector.print_hardware_info(hardware_info)

    # 推荐配置
    config = detector.recommend_qwen_asr_config(hardware_info)
    detector.print_recommended_config(config)

    # 打印 Python 代码示例
    print("=" * 60)
    print("使用推荐配置的代码示例:")
    print("=" * 60)
    print(f"""
import torch
from qwen_asr import Qwen3ASRModel

# 创建模型
asr_model = Qwen3ASRModel.from_pretrained(
    "{config['model']}",
    dtype=torch.{config.get('dtype', 'float32')},
    device_map="{config['device']}" if "{config['device']}" != "cpu" else None,
    max_inference_batch_size=8,
    max_new_tokens=256,
)

# 执行识别
results = asr_model.transcribe(
    audio="your_audio.mp4",
    language=None,  # 自动检测语言
)

# 获取结果
print(f"识别语言: {{results[0].language}}")
print(f"识别文本: {{results[0].text}}")
""")


if __name__ == "__main__":
    # 导入 os 用于 cpu_count 备用
    import os
    main()
