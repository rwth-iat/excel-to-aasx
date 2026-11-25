import pytest

from excel_to_aasx.domain.diagram_source import single_uml_diagram


def test_bare_source_is_wrapped_like_asciidoctor_diagram_does():
    assert single_uml_diagram("class A") == "@startuml\nclass A\n@enduml\n"


def test_complete_diagram_is_kept():
    text = "@startuml Overview\nclass A\n@enduml"
    assert single_uml_diagram(f"\n{text}\n\n") == text + "\n"


@pytest.mark.parametrize(
    "source",
    [
        "@startuml\nclass A\n@enduml\n@startuml\nclass B\n@enduml",  # two renders for one
        "@startditaa\n+--+\n@endditaa",
        "@startlatex\n\\frac{1}{2}\n@endlatex",
        "class A\n@enduml\n@startjson\n{}",  # smuggled into a bare block
        "@startuml\nclass A",
        "@startuml\nclass A\n@enduml\ntrailing",
    ],
)
def test_other_diagram_types_and_several_diagrams_are_refused(source):
    with pytest.raises(ValueError, match="one @startuml|end with @enduml"):
        single_uml_diagram(source)


def test_multi_page_diagrams_are_refused():
    with pytest.raises(ValueError, match="newpage"):
        single_uml_diagram("class A\nnewpage\nclass B")
