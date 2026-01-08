class MockResult:
    def __init__(self, validated_output=None, failures=None):
        self.validated_output = validated_output
        self.failures = failures

class MockFailure:
    def __init__(self, msg):
        self.failure_message = msg