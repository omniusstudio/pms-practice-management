#!/usr/bin/env python3
"""Script to validate test pyramid structure and coverage requirements."""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Dict, List, Tuple


class TestPyramidValidator:
    """Validates test pyramid structure and coverage requirements."""
    
    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.backend_path = self.project_root / "apps" / "backend"
        self.frontend_path = self.project_root / "apps" / "frontend"
        self.e2e_path = self.project_root / "tests" / "e2e"
        
        # Coverage thresholds
        self.coverage_thresholds = {
            "unit": 85,
            "integration": 70,
            "critical": 90,
            "hipaa": 100,
            "overall": 80
        }
    
    def validate_test_structure(self) -> List[str]:
        """Validate test directory structure."""
        issues = []
        
        # Check backend test structure
        backend_test_dirs = [
            self.backend_path / "tests" / "unit",
            self.backend_path / "tests" / "integration",
            self.backend_path / "tests" / "smoke",
        ]
        
        for test_dir in backend_test_dirs:
            if not test_dir.exists():
                issues.append(f"Missing test directory: {test_dir}")
            elif not any(test_dir.glob("test_*.py")):
                issues.append(f"No test files found in: {test_dir}")
        
        # Check E2E test structure
        if not self.e2e_path.exists():
            issues.append(f"Missing E2E test directory: {self.e2e_path}")
        elif not (self.e2e_path / "playwright.config.ts").exists():
            issues.append("Missing Playwright configuration")
        
        # Check performance test structure
        perf_test_path = self.project_root / "tests" / "performance"
        if not perf_test_path.exists():
            issues.append(f"Missing performance test directory: {perf_test_path}")
        elif not (perf_test_path / "artillery.yml").exists():
            issues.append("Missing Artillery configuration")
        
        return issues
    
    def run_backend_tests_with_coverage(self) -> Tuple[bool, Dict]:
        """Run backend tests and collect coverage data."""
        os.chdir(self.backend_path)
        
        try:
            # Run tests with coverage
            result = subprocess.run([
                "python", "-m", "pytest",
                "--cov=.",
                "--cov-report=json",
                "--cov-report=term",
                "-v",
                "--tb=short"
            ], capture_output=True, text=True, timeout=300)
            
            # Parse coverage report
            coverage_file = self.backend_path / "coverage.json"
            coverage_data = {}
            
            if coverage_file.exists():
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
            
            return result.returncode == 0, {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "coverage": coverage_data,
                "returncode": result.returncode
            }
            
        except subprocess.TimeoutExpired:
            return False, {"error": "Tests timed out after 5 minutes"}
        except Exception as e:
            return False, {"error": str(e)}
    
    def analyze_test_distribution(self) -> Dict[str, int]:
        """Analyze distribution of tests across the pyramid."""
        test_counts = {
            "unit": 0,
            "integration": 0,
            "e2e": 0,
            "smoke": 0,
            "performance": 0
        }
        
        # Count backend unit tests
        unit_dir = self.backend_path / "tests" / "unit"
        if unit_dir.exists():
            test_counts["unit"] = len(list(unit_dir.glob("test_*.py")))
        
        # Count backend integration tests
        integration_dir = self.backend_path / "tests" / "integration"
        if integration_dir.exists():
            integration_files = list(integration_dir.glob("test_*.py"))
            test_counts["integration"] = len(integration_files)
        
        # Count smoke tests
        smoke_dir = self.backend_path / "tests" / "smoke"
        if smoke_dir.exists():
            test_counts["smoke"] = len(list(smoke_dir.glob("test_*.py")))
        
        # Count E2E tests
        if self.e2e_path.exists():
            specs_dir = self.e2e_path / "specs"
            if specs_dir.exists():
                test_counts["e2e"] = len(list(specs_dir.glob("*.spec.ts")))
        
        # Count performance tests
        perf_dir = self.project_root / "tests" / "performance"
        if perf_dir.exists():
            yml_files = list(perf_dir.glob("*.yml"))
            yaml_files = list(perf_dir.glob("*.yaml"))
            test_counts["performance"] = len(yml_files + yaml_files)
        
        return test_counts
    
    def validate_test_markers(self) -> List[str]:
        """Validate that tests have proper markers."""
        issues = []
        
        # Check pytest.ini for required markers
        pytest_ini = self.backend_path / "pytest.ini"
        if not pytest_ini.exists():
            issues.append("Missing pytest.ini configuration")
            return issues
        
        with open(pytest_ini) as f:
            content = f.read()
        
        required_markers = [
            "unit", "integration", "e2e", "smoke", "security",
            "hipaa", "performance", "critical"
        ]
        
        for marker in required_markers:
            if f"{marker}:" not in content:
                issues.append(f"Missing pytest marker: {marker}")
        
        return issues
    
    def check_critical_test_coverage(self) -> List[str]:
        """Check that critical paths have adequate test coverage."""
        issues = []
        
        # Define critical test files that must exist
        critical_tests = [
            self.backend_path / "tests" / "unit" / "test_auth.py",
            self.backend_path / "tests" / "integration" / "test_api_endpoints.py",
            self.backend_path / "tests" / "smoke" / "test_deployment.py",
        ]
        
        for test_file in critical_tests:
            if not test_file.exists():
                issues.append(f"Missing critical test file: {test_file.name}")
        
        return issues
    
    def validate_ci_configuration(self) -> List[str]:
        """Validate CI configuration for test gates."""
        issues = []
        
        ci_file = self.project_root / ".github" / "workflows" / "ci.yml"
        if not ci_file.exists():
            issues.append("Missing CI workflow configuration")
            return issues
        
        with open(ci_file) as f:
            ci_content = f.read()
        
        # Check for required CI jobs
        required_jobs = [
            "quality-gate",
            "test-backend",
            "test-frontend"
        ]
        
        for job in required_jobs:
            if job not in ci_content:
                issues.append(f"Missing CI job: {job}")
        
        # Check for coverage enforcement
        if "--cov-fail-under" not in ci_content:
            issues.append("CI does not enforce coverage thresholds")
        
        return issues
    
    def generate_report(self) -> Dict:
        """Generate comprehensive test pyramid validation report."""
        print("🔍 Validating test pyramid structure...")
        
        report = {
            "structure_issues": self.validate_test_structure(),
            "marker_issues": self.validate_test_markers(),
            "critical_test_issues": self.check_critical_test_coverage(),
            "ci_issues": self.validate_ci_configuration(),
            "test_distribution": self.analyze_test_distribution(),
            "coverage_thresholds": self.coverage_thresholds
        }
        
        # Run backend tests if structure is valid
        if not report["structure_issues"]:
            print("🧪 Running backend tests with coverage...")
            success, test_results = self.run_backend_tests_with_coverage()
            report["test_results"] = test_results
            report["tests_passed"] = success
        else:
            report["tests_passed"] = False
            report["test_results"] = {
                "error": "Skipped due to structure issues"
            }
        
        return report
    
    def print_report(self, report: Dict) -> bool:
        """Print validation report and return success status."""
        print("\n" + "=" * 60)
        print("📊 TEST PYRAMID VALIDATION REPORT")
        print("=" * 60)
        
        all_good = True
        
        # Structure issues
        if report["structure_issues"]:
            print("\n❌ STRUCTURE ISSUES:")
            for issue in report["structure_issues"]:
                print(f"  • {issue}")
            all_good = False
        else:
            print("\n✅ Test structure is valid")
        
        # Marker issues
        if report["marker_issues"]:
            print("\n❌ MARKER ISSUES:")
            for issue in report["marker_issues"]:
                print(f"  • {issue}")
            all_good = False
        else:
            print("✅ Test markers are properly configured")
        
        # Critical test issues
        if report["critical_test_issues"]:
            print("\n❌ CRITICAL TEST ISSUES:")
            for issue in report["critical_test_issues"]:
                print(f"  • {issue}")
            all_good = False
        else:
            print("✅ Critical tests are present")
        
        # CI issues
        if report["ci_issues"]:
            print("\n❌ CI CONFIGURATION ISSUES:")
            for issue in report["ci_issues"]:
                print(f"  • {issue}")
            all_good = False
        else:
            print("✅ CI configuration is valid")
        
        # Test distribution
        print("\n📈 TEST DISTRIBUTION:")
        distribution = report["test_distribution"]
        total_tests = sum(distribution.values())
        
        for test_type, count in distribution.items():
            percentage = (count / total_tests * 100) if total_tests > 0 else 0
            print(f"  • {test_type.capitalize()}: {count} ({percentage:.1f}%)")
        
        # Validate pyramid ratios
        if total_tests > 0:
            unit_ratio = distribution["unit"] / total_tests
            integration_ratio = distribution["integration"] / total_tests
            e2e_ratio = distribution["e2e"] / total_tests
            
            print("\n🔺 PYRAMID VALIDATION:")
            
            # Unit tests should be 60-80% of total
            if unit_ratio < 0.6:
                print(
                    f"  ⚠️  Unit tests ({unit_ratio:.1%}) below 60%"
                )
                all_good = False
            elif unit_ratio > 0.8:
                print(
                    f"  ⚠️  Unit tests ({unit_ratio:.1%}) above 80%"
                )
            else:
                print(
                    f"  ✅ Unit tests ({unit_ratio:.1%}) in good range"
                )
            
            # Integration tests should be 15-25% of total
            if integration_ratio < 0.15:
                print(
                    f"  ⚠️  Integration tests ({integration_ratio:.1%}) "
                    "below 15%"
                )
                all_good = False
            elif integration_ratio > 0.25:
                print(
                    f"  ⚠️  Integration tests ({integration_ratio:.1%}) "
                    "above 25%"
                )
            else:
                print(
                    f"  ✅ Integration tests ({integration_ratio:.1%}) "
                    "in good range"
                )
            
            # E2E tests should be 5-15% of total
            if e2e_ratio > 0.15:
                print(f"  ⚠️  E2E tests ({e2e_ratio:.1%}) above 15%")
            else:
                print(f"  ✅ E2E tests ({e2e_ratio:.1%}) in acceptable range")
        
        # Test results
        if "test_results" in report:
            print("\n🧪 TEST EXECUTION:")
            if report["tests_passed"]:
                print("  ✅ All tests passed")
            else:
                print("  ❌ Some tests failed")
                all_good = False
                
                if "error" in report["test_results"]:
                    print(f"  Error: {report['test_results']['error']}")
        
        print("\n" + "=" * 60)
        if all_good:
            print("🎉 TEST PYRAMID VALIDATION PASSED")
        else:
            print("💥 TEST PYRAMID VALIDATION FAILED")
        print("=" * 60)
        
        return all_good


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        project_root = sys.argv[1]
    else:
        project_root = os.getcwd()
    
    validator = TestPyramidValidator(project_root)
    report = validator.generate_report()
    success = validator.print_report(report)
    
    # Save report to file
    report_file = Path(project_root) / "test_pyramid_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2, default=str)
    
    print(f"\n📄 Full report saved to: {report_file}")
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()