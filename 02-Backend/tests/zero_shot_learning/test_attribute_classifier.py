from zero_shot_learning.attribute_classifier import AttributeClassifier, AttributeSpec, ClassDescriptor


def test_register_and_classify():
    classifier = AttributeClassifier()
    classifier.register_class(ClassDescriptor(name="fruit", attributes={"color": ["red", "yellow"], "taste": ["sweet"]}))
    classifier.register_class(ClassDescriptor(name="vegetable", attributes={"color": ["green"], "taste": ["savory"]}))
    result = classifier.classify({"color": ["red"], "taste": ["sweet"]})
    assert result == "fruit"


def test_classify_no_match():
    classifier = AttributeClassifier()
    classifier.register_class(ClassDescriptor(name="fruit", attributes={"color": ["red"]}))
    result = classifier.classify({"color": ["blue"], "taste": ["sour"]})
    assert result is None


def test_classify_with_scores():
    classifier = AttributeClassifier()
    classifier.register_class(ClassDescriptor(name="cat", attributes={"legs": ["4"], "sound": ["meow"]}))
    classifier.register_class(ClassDescriptor(name="dog", attributes={"legs": ["4"], "sound": ["bark"]}))
    scores = classifier.classify_with_scores({"legs": ["4"], "sound": ["meow"]})
    assert scores[0][0] == "cat"
    assert scores[0][1] > 0


def test_list_classes():
    classifier = AttributeClassifier()
    classifier.register_class(ClassDescriptor(name="a", attributes={}))
    classifier.register_class(ClassDescriptor(name="b", attributes={}))
    assert set(classifier.list_classes()) == {"a", "b"}
