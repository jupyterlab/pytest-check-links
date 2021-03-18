

```
git pull origin master
git tag ${NEW_VERSION}
rm -rf dist build
python setup.py sdist
python setup.py bdist_wheel
twine check dist/* && twine upload dist/*
git push origin master --tags
```
