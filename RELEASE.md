

```
git pull origin master
git tag ${NEW_VERSION}
rm -rf dist build
python setup.py sdist
twine check dist/* && twine upload dist/*
git push origin master --tags
```
